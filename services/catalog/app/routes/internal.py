"""
Internal endpoints called by other Prism Affiliate services and by PRISM worker.
No authentication required (Docker-network only).
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Product

router = APIRouter()


class ProductSummary(BaseModel):
    id: str
    marketplace: str
    external_id: str
    title: str
    description: Optional[str]
    price: float
    currency: str
    image_url: str
    product_url: str
    commission_rate: float
    rating: Optional[float]
    review_count: Optional[int]
    discount_pct: Optional[float]
    tags: list


@router.get("/products/for-project/{project_id}", response_model=list[ProductSummary])
async def products_for_project(
    project_id: str,
    niche: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    marketplace: Optional[str] = Query(None, description="Comma-separated list"),
    min_commission: Optional[float] = Query(None),
    has_image: bool = Query(False),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by PRISM pipeline worker to get best products for a project.
    Returns top products scored by commission rate + rating.
    """
    filters = [Product.is_active == True, Product.in_stock == True]
    if niche:
        filters.append(Product.niche == niche)
    if category:
        filters.append(Product.category.ilike(f"%{category}%"))
    if marketplace:
        mkts = [m.strip() for m in marketplace.split(",")]
        filters.append(Product.marketplace.in_(mkts))
    if min_commission is not None:
        filters.append(Product.commission_rate >= min_commission)
    if has_image:
        filters.append(Product.image_url != "")

    stmt = (
        select(Product)
        .where(and_(*filters))
        .order_by(Product.commission_rate.desc(), Product.rating.desc().nulls_last())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/products/{product_id}/summary", response_model=ProductSummary)
async def product_summary(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


class AccountBrief(BaseModel):
    id: str
    marketplace: str
    credentials_encrypted: str
    campaign_external_id: Optional[str] = None


@router.get("/account-for-product/{product_id}", response_model=AccountBrief)
async def account_for_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Returns the marketplace account (with encrypted credentials) for a product."""
    from fastapi import HTTPException
    from app.models import MarketplaceAccount, Campaign
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    account = await db.get(MarketplaceAccount, product.marketplace_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    campaign_external_id = None
    if product.campaign_id:
        # campaign_id in products stores external_campaign_id, not UUID
        stmt = select(Campaign).where(
            Campaign.external_campaign_id == product.campaign_id,
            Campaign.marketplace_account_id == product.marketplace_account_id,
        ).limit(1)
        camp_result = await db.execute(stmt)
        campaign = camp_result.scalar_one_or_none()
        if campaign:
            campaign_external_id = campaign.external_campaign_id
        else:
            # Fallback: campaign_id is already the external ID
            campaign_external_id = product.campaign_id

    return AccountBrief(
        id=account.id,
        marketplace=account.marketplace.value,
        credentials_encrypted=account.credentials_encrypted,
        campaign_external_id=campaign_external_id,
    )
