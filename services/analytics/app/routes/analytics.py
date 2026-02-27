from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AffiliateStats
from app.deps import require_auth

router = APIRouter()


class OverviewOut(BaseModel):
    total_clicks: int
    total_conversions: int
    total_revenue: float
    total_commission: float
    period_days: int


class StatsByDimension(BaseModel):
    dimension: str
    clicks: int
    conversions: int
    revenue: float
    commission: float


def _period_start(days: int) -> date:
    return date.today() - timedelta(days=days)


@router.get("/overview", response_model=OverviewOut)
async def overview(
    period: int = Query(30, description="Days to look back"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    since = _period_start(period)
    result = await db.execute(
        select(
            func.sum(AffiliateStats.clicks),
            func.sum(AffiliateStats.conversions),
            func.sum(AffiliateStats.revenue),
            func.sum(AffiliateStats.commission),
        ).where(AffiliateStats.stat_date >= since)
    )
    row = result.one()
    return OverviewOut(
        total_clicks=int(row[0] or 0),
        total_conversions=int(row[1] or 0),
        total_revenue=float(row[2] or 0),
        total_commission=float(row[3] or 0),
        period_days=period,
    )


@router.get("/by-marketplace", response_model=list[StatsByDimension])
async def by_marketplace(
    period: int = Query(30),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    since = _period_start(period)
    result = await db.execute(
        select(
            AffiliateStats.marketplace,
            func.sum(AffiliateStats.clicks),
            func.sum(AffiliateStats.conversions),
            func.sum(AffiliateStats.revenue),
            func.sum(AffiliateStats.commission),
        )
        .where(AffiliateStats.stat_date >= since)
        .group_by(AffiliateStats.marketplace)
        .order_by(func.sum(AffiliateStats.revenue).desc())
    )
    return [
        StatsByDimension(
            dimension=row[0],
            clicks=int(row[1] or 0),
            conversions=int(row[2] or 0),
            revenue=float(row[3] or 0),
            commission=float(row[4] or 0),
        )
        for row in result
    ]


@router.get("/by-product", response_model=list[StatsByDimension])
async def by_product(
    period: int = Query(30),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    since = _period_start(period)
    result = await db.execute(
        select(
            AffiliateStats.product_id,
            func.sum(AffiliateStats.clicks),
            func.sum(AffiliateStats.conversions),
            func.sum(AffiliateStats.revenue),
            func.sum(AffiliateStats.commission),
        )
        .where(AffiliateStats.stat_date >= since, AffiliateStats.product_id.is_not(None))
        .group_by(AffiliateStats.product_id)
        .order_by(func.sum(AffiliateStats.revenue).desc())
        .limit(limit)
    )
    return [
        StatsByDimension(
            dimension=row[0],
            clicks=int(row[1] or 0),
            conversions=int(row[2] or 0),
            revenue=float(row[3] or 0),
            commission=float(row[4] or 0),
        )
        for row in result
    ]


@router.get("/by-project", response_model=list[StatsByDimension])
async def by_project(
    period: int = Query(30),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    since = _period_start(period)
    result = await db.execute(
        select(
            AffiliateStats.prism_project_id,
            func.sum(AffiliateStats.clicks),
            func.sum(AffiliateStats.conversions),
            func.sum(AffiliateStats.revenue),
            func.sum(AffiliateStats.commission),
        )
        .where(AffiliateStats.stat_date >= since, AffiliateStats.prism_project_id.is_not(None))
        .group_by(AffiliateStats.prism_project_id)
        .order_by(func.sum(AffiliateStats.revenue).desc())
    )
    return [
        StatsByDimension(
            dimension=row[0],
            clicks=int(row[1] or 0),
            conversions=int(row[2] or 0),
            revenue=float(row[3] or 0),
            commission=float(row[4] or 0),
        )
        for row in result
    ]
