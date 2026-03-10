"""
Feed ingestion tasks.
Downloads product feeds from Admitad/GdeSlon/other marketplaces,
parses them and upserts products into catalog-db.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery_app
from app.config import settings
from shared.adapters import get_adapter
from shared.encryption import decrypt_json

logger = logging.getLogger(__name__)


def _make_catalog_session() -> async_sessionmaker:
    engine = create_async_engine(settings.catalog_db_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="affiliate.dispatch_feed_syncs")
def dispatch_feed_syncs():
    """Check all active feeds and dispatch sync tasks for those due."""
    asyncio.run(_dispatch_feed_syncs())


async def _dispatch_feed_syncs():
    from app.tasks._catalog_models import ProductFeed
    SessionLocal = _make_catalog_session()
    async with SessionLocal() as db:
        result = await db.execute(
            select(ProductFeed).where(
                ProductFeed.status.in_(["active", "error", "syncing"])
            )
        )
        feeds = result.scalars().all()

    for feed in feeds:
        sync_feed.delay(feed.id)


@celery_app.task(name="affiliate.sync_feed", bind=True, max_retries=3)
def sync_feed(self, feed_id: str):
    """Download and process a single product feed."""
    try:
        asyncio.run(_sync_feed(feed_id))
    except Exception as exc:
        logger.error(f"Feed sync failed for {feed_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


async def _sync_feed(feed_id: str):
    from app.tasks._catalog_models import ProductFeed, MarketplaceAccount, Product
    from sys import modules

    # Dynamic import of YML parser (service code isn't in worker package)
    import importlib.util, os

    SessionLocal = _make_catalog_session()
    async with SessionLocal() as db:
        feed = await db.get(ProductFeed, feed_id)
        if not feed:
            logger.warning(f"Feed {feed_id} not found")
            return

        account = await db.get(MarketplaceAccount, feed.marketplace_account_id)
        if not account:
            logger.error(f"No account for feed {feed_id}")
            return

        # Mark syncing
        feed.status = "syncing"
        await db.commit()

    try:
        credentials = decrypt_json(account.credentials_encrypted, settings.encryption_key)
        adapter = get_adapter(account.marketplace)

        # Download raw feed bytes
        raw = adapter.fetch_feed(feed.feed_url, credentials)

        # Parse based on format
        fmt = feed.feed_format.value if hasattr(feed.feed_format, "value") else feed.feed_format
        products_data = _parse_feed(raw, fmt, feed.niche_mapping, feed.category_mapping)

        # Upsert products
        count = await _upsert_products(
            products_data=products_data,
            marketplace=account.marketplace,
            marketplace_account_id=account.id,
            campaign_id=feed.campaign_id,
            feed_id=feed_id,
        )

        async with SessionLocal() as db:
            feed = await db.get(ProductFeed, feed_id)
            feed.status = "active"
            feed.last_sync_at = datetime.utcnow()
            feed.last_sync_products = count
            feed.last_error = None
            await db.commit()

        logger.info(f"Feed {feed_id} synced: {count} products")

    except Exception as exc:
        async with SessionLocal() as db:
            feed = await db.get(ProductFeed, feed_id)
            if feed:
                feed.status = "error"
                feed.last_error = str(exc)[:1000]
                await db.commit()
        raise


def _parse_feed(raw: bytes, fmt: str, niche_mapping: dict, category_mapping: dict) -> list[dict]:
    if fmt in ("yml", "xml"):
        from shared.adapters.gdeslon import GdeSlonAdapter
        adapter = GdeSlonAdapter()
        results = adapter._parse_yml_response(raw)
        # Convert dataclasses to dicts
        parsed = []
        for r in results:
            niche = niche_mapping.get(r.category)
            category = category_mapping.get(r.category, r.category)
            parsed.append({
                "external_id": r.external_id,
                "title": r.title,
                "description": r.description[:2000] if r.description else None,
                "category": category,
                "brand": r.brand,
                "price": r.price,
                "currency": r.currency,
                "original_price": r.original_price,
                "discount_pct": r.discount_pct,
                "image_url": r.image_url,
                "product_url": r.product_url,
                "rating": r.rating,
                "review_count": r.review_count,
                "in_stock": r.in_stock,
                "commission_rate": r.commission_rate,
                "commission_type": r.commission_type,
                "tags": r.tags,
                "niche": niche,
            })
        return parsed
    raise ValueError(f"Unsupported feed format: {fmt}")


async def _upsert_products(
    products_data: list[dict],
    marketplace: str,
    marketplace_account_id: str,
    feed_id: str,
    campaign_id: str | None = None,
) -> int:
    from app.tasks._catalog_models import Product
    SessionLocal = _make_catalog_session()
    now = datetime.utcnow()
    count = 0

    async with SessionLocal() as db:
        for chunk in _chunks(products_data, 500):
            for p in chunk:
                stmt = pg_insert(Product).values(
                    external_id=p["external_id"],
                    marketplace=marketplace,
                    marketplace_account_id=marketplace_account_id,
                    campaign_id=campaign_id,
                    feed_id=feed_id,
                    title=p["title"],
                    description=p.get("description"),
                    category=p.get("category", ""),
                    brand=p.get("brand"),
                    price=p["price"],
                    currency=p.get("currency", "RUB"),
                    original_price=p.get("original_price"),
                    discount_pct=p.get("discount_pct"),
                    image_url=p.get("image_url", ""),
                    product_url=p["product_url"],
                    rating=p.get("rating"),
                    review_count=p.get("review_count"),
                    in_stock=p.get("in_stock", True),
                    commission_rate=p.get("commission_rate", 0.0),
                    commission_type=p.get("commission_type", "percentage"),
                    tags=p.get("tags", []),
                    niche=p.get("niche"),
                    last_seen_at=now,
                    is_active=True,
                ).on_conflict_do_update(
                    constraint="uq_marketplace_product",
                    set_={
                        "title": p["title"],
                        "price": p["price"],
                        "original_price": p.get("original_price"),
                        "discount_pct": p.get("discount_pct"),
                        "in_stock": p.get("in_stock", True),
                        "commission_rate": p.get("commission_rate", 0.0),
                        "image_url": p.get("image_url", ""),
                        "last_seen_at": now,
                        "is_active": True,
                    }
                )
                await db.execute(stmt)
                count += 1
            await db.commit()

    return count


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
