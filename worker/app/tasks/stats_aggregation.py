"""
Daily stats aggregation task.
Reads click_events and conversion_events from tracker-db,
writes aggregated rows into analytics-db.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

_tracker_engine = None
_tracker_session_factory = None
_analytics_engine = None
_analytics_session_factory = None


def _make_tracker_session():
    from sqlalchemy.ext.asyncio import AsyncSession
    global _tracker_engine, _tracker_session_factory
    if _tracker_engine is None:
        _tracker_engine = create_async_engine(settings.tracker_db_url, pool_pre_ping=True, pool_recycle=3600)
        _tracker_session_factory = async_sessionmaker(_tracker_engine, class_=AsyncSession, expire_on_commit=False)
    return _tracker_session_factory()


def _make_analytics_session():
    from sqlalchemy.ext.asyncio import AsyncSession
    global _analytics_engine, _analytics_session_factory
    if _analytics_engine is None:
        _analytics_engine = create_async_engine(settings.analytics_db_url, pool_pre_ping=True, pool_recycle=3600)
        _analytics_session_factory = async_sessionmaker(_analytics_engine, class_=AsyncSession, expire_on_commit=False)
    return _analytics_session_factory()


@celery_app.task(name="affiliate.aggregate_daily_stats")
def aggregate_daily_stats():
    asyncio.run(_aggregate_daily_stats())


async def _aggregate_daily_stats():
    from app.tasks._tracker_models import ClickEvent, ConversionEvent
    from app.tasks._analytics_models import AffiliateStats

    yesterday = date.today() - timedelta(days=1)

    async with _make_tracker_session() as db:
        # Aggregate clicks by product + project
        click_result = await db.execute(
            select(
                ClickEvent.product_id,
                ClickEvent.marketplace,
                ClickEvent.prism_project_id,
                ClickEvent.prism_content_id,
                func.count(ClickEvent.id).label("clicks"),
            )
            .where(func.date(ClickEvent.clicked_at) == yesterday)
            .group_by(
                ClickEvent.product_id,
                ClickEvent.marketplace,
                ClickEvent.prism_project_id,
                ClickEvent.prism_content_id,
            )
        )
        click_rows = click_result.all()

        # Aggregate conversions
        conv_result = await db.execute(
            select(
                ConversionEvent.product_id,
                ConversionEvent.marketplace,
                ConversionEvent.prism_project_id,
                ConversionEvent.prism_content_id,
                func.count(ConversionEvent.id).label("conversions"),
                func.sum(ConversionEvent.order_amount).label("revenue"),
                func.sum(ConversionEvent.commission_amount).label("commission"),
            )
            .where(func.date(ConversionEvent.reported_at) == yesterday)
            .group_by(
                ConversionEvent.product_id,
                ConversionEvent.marketplace,
                ConversionEvent.prism_project_id,
                ConversionEvent.prism_content_id,
            )
        )
        conv_rows = conv_result.all()

    # Build aggregated dict
    stats: dict[tuple, dict] = {}
    for row in click_rows:
        key = (row.product_id, row.marketplace, row.prism_project_id, row.prism_content_id)
        stats[key] = {"clicks": row.clicks, "conversions": 0, "revenue": 0.0, "commission": 0.0}

    for row in conv_rows:
        key = (row.product_id, row.marketplace, row.prism_project_id, row.prism_content_id)
        if key not in stats:
            stats[key] = {"clicks": 0, "conversions": 0, "revenue": 0.0, "commission": 0.0}
        stats[key]["conversions"] = row.conversions
        stats[key]["revenue"] = float(row.revenue or 0)
        stats[key]["commission"] = float(row.commission or 0)

    async with _make_analytics_session() as db:
        for (product_id, marketplace, project_id, content_id), values in stats.items():
            stmt = pg_insert(AffiliateStats).values(
                stat_date=yesterday,
                marketplace=marketplace,
                product_id=product_id,
                prism_project_id=project_id,
                prism_content_id=content_id,
                **values,
            ).on_conflict_do_update(
                constraint="uq_daily_stats",
                set_=values,
            )
            await db.execute(stmt)
        await db.commit()

    logger.info(f"Aggregated {len(stats)} stat rows for {yesterday}")
