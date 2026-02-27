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
from app.models import AffiliateLink
from app.services.link_generator import generate_link_for_product
from app.config import settings

router = APIRouter()


class BulkLinkRequest(BaseModel):
    product_ids: list[str]
    prism_content_id: Optional[str] = None
    prism_project_id: Optional[str] = None


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
            link_data = await generate_link_for_product(
                product_id=product_id,
                catalog_url=settings.catalog_service_url,
                encryption_key=settings.encryption_key,
            )
            link = AffiliateLink(
                product_id=product_id,
                marketplace=link_data["marketplace"],
                marketplace_account_id=link_data["marketplace_account_id"],
                affiliate_url=link_data["affiliate_url"],
                short_code=link_data["short_code"],
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
