"""
Refresh affiliate links that are nearing expiration.
Flipkart links expire in 10 hours — must be regenerated.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

_links_engine = None
_links_session_factory = None


def _make_links_session():
    from sqlalchemy.ext.asyncio import AsyncSession
    global _links_engine, _links_session_factory
    if _links_engine is None:
        _links_engine = create_async_engine(settings.links_db_url, pool_pre_ping=True, pool_recycle=3600)
        _links_session_factory = async_sessionmaker(_links_engine, class_=AsyncSession, expire_on_commit=False)
    return _links_session_factory()


@celery_app.task(name="affiliate.refresh_expiring_links")
def refresh_expiring_links():
    asyncio.run(_refresh_expiring_links())


async def _refresh_expiring_links():
    from app.tasks._links_models import AffiliateLink
    threshold = datetime.utcnow() + timedelta(hours=2)

    async with _make_links_session() as db:
        result = await db.execute(
            select(AffiliateLink).where(
                AffiliateLink.expires_at <= threshold,
                AffiliateLink.is_active == True,
            )
        )
        expiring = result.scalars().all()

    if not expiring:
        return

    logger.info(f"Refreshing {len(expiring)} expiring links")

    async with httpx.AsyncClient(timeout=10) as client:
        for link in expiring:
            try:
                resp = await client.post(
                    f"{settings.links_service_url}/internal/links/generate-for-content",
                    json={
                        "product_ids": [link.product_id],
                        "prism_content_id": link.prism_content_id,
                        "prism_project_id": link.prism_project_id,
                    },
                )
                resp.raise_for_status()
                async with _make_links_session() as db:
                    old_link = await db.get(AffiliateLink, link.id)
                    if old_link:
                        old_link.is_active = False
                    await db.commit()
            except Exception as exc:
                logger.error(f"Failed to refresh link {link.id}: {exc}")
