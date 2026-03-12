"""
Internal endpoints called by PRISM pipeline worker and tracker service.
No authentication — Docker-network only.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AffiliateLink, SelectionProfile
from app.services.link_generator import generate_link_for_product
from app.config import settings

router = APIRouter()


class BulkLinkRequest(BaseModel):
    product_ids: list[str]
    prism_content_id: Optional[str] = None
    prism_project_id: Optional[str] = None
    channel: Optional[str] = None  # "pinterest" | "telegram" | None
    sub_id_prefix: Optional[str] = None  # prefix for auto-generated subid


class LinkBrief(BaseModel):
    product_id: str
    affiliate_url: str
    short_code: str
    marketplace: str


class ResolveResponse(BaseModel):
    affiliate_url: str
    product_id: str


@router.post("/links/generate-for-content", response_model=list[LinkBrief])
async def generate_for_content(
    body: BulkLinkRequest,
    db: AsyncSession = Depends(get_db),
):
    """Called by PRISM pipeline worker before publishing."""
    results = []
    for product_id in body.product_ids:
        try:
            # Build sub_id from prefix + product_id fragment when channel is set
            sub_id = None
            if body.channel and body.sub_id_prefix:
                sub_id = f"{body.sub_id_prefix}_{product_id[:8]}"
            elif body.channel:
                sub_id = product_id[:8]

            link_data = await generate_link_for_product(
                product_id=product_id,
                catalog_url=settings.catalog_service_url,
                encryption_key=settings.encryption_key,
                sub_id=sub_id,
                channel=body.channel,
            )
            link = AffiliateLink(
                product_id=product_id,
                marketplace=link_data["marketplace"],
                marketplace_account_id=link_data["marketplace_account_id"],
                affiliate_url=link_data["affiliate_url"],
                short_code=link_data["short_code"],
                sub_id=link_data["sub_id"],
                channel=link_data["channel"],
                prism_content_id=body.prism_content_id,
                prism_project_id=body.prism_project_id,
            )
            db.add(link)
            await db.flush()
            results.append(LinkBrief(
                product_id=product_id,
                affiliate_url=link_data["affiliate_url"],
                short_code=link_data["short_code"],
                marketplace=link_data["marketplace"],
            ))
        except Exception:
            continue
    await db.commit()
    return results


@router.get("/selection-profiles")
async def internal_list_profiles(
    prism_project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Internal: list selection profiles (no JWT). Used by bridge worker."""
    stmt = select(SelectionProfile).where(SelectionProfile.is_active == True)
    if prism_project_id:
        stmt = stmt.where(SelectionProfile.prism_project_id == prism_project_id)
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    return [
        {
            "id": p.id,
            "prism_project_id": p.prism_project_id,
            "name": p.name,
            "marketplaces": p.marketplaces,
            "categories": p.categories,
            "keywords": p.keywords,
            "min_commission_rate": p.min_commission_rate,
            "min_rating": p.min_rating,
            "max_products": p.max_products,
            "sort_by": p.sort_by,
            "is_active": p.is_active,
        }
        for p in profiles
    ]


@router.get("/links/by-subid/{sub_id}")
async def get_link_by_subid(sub_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AffiliateLink).where(AffiliateLink.sub_id == sub_id)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return {
        "id": link.id,
        "product_id": link.product_id,
        "affiliate_url": link.affiliate_url,
        "prism_content_id": link.prism_content_id,
        "prism_project_id": link.prism_project_id,
    }


@router.get("/links/resolve/{short_code}", response_model=ResolveResponse)
async def resolve_short_code(
    short_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Called by tracker service to resolve a short_code to affiliate_url."""
    result = await db.execute(
        select(AffiliateLink).where(
            AffiliateLink.short_code == short_code,
            AffiliateLink.is_active == True,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return ResolveResponse(affiliate_url=link.affiliate_url, product_id=link.product_id)
