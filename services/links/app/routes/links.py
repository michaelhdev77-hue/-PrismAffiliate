from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import AffiliateLink
from app.services.link_generator import generate_link_for_product, generate_short_code
from app.config import settings

router = APIRouter()


class LinkGenerateRequest(BaseModel):
    product_id: str
    prism_content_id: Optional[str] = None
    prism_project_id: Optional[str] = None
    sub_id: Optional[str] = None


class LinkOut(BaseModel):
    id: str
    product_id: str
    marketplace: str
    affiliate_url: str
    short_code: str
    prism_content_id: Optional[str]
    prism_project_id: Optional[str]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/generate", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def generate_link(
    body: LinkGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    try:
        link_data = await generate_link_for_product(
            product_id=body.product_id,
            catalog_url=settings.catalog_service_url,
            encryption_key=settings.encryption_key,
            sub_id=body.sub_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Link generation failed: {exc}")

    link = AffiliateLink(
        product_id=body.product_id,
        marketplace=link_data["marketplace"],
        marketplace_account_id=link_data["marketplace_account_id"],
        affiliate_url=link_data["affiliate_url"],
        short_code=link_data["short_code"],
        prism_content_id=body.prism_content_id,
        prism_project_id=body.prism_project_id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


class BulkGenerateRequest(BaseModel):
    product_ids: list[str]
    prism_project_id: Optional[str] = None


class BulkGenerateResult(BaseModel):
    created: int
    failed: int
    links: list[LinkOut]


@router.post("/generate-bulk", response_model=BulkGenerateResult, status_code=status.HTTP_201_CREATED)
async def generate_bulk_links(
    body: BulkGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    """Generate affiliate links for multiple products at once."""
    created_links = []
    failed = 0
    for product_id in body.product_ids:
        # Skip if link already exists
        existing = await db.execute(
            select(AffiliateLink).where(
                AffiliateLink.product_id == product_id,
                AffiliateLink.is_active == True,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

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
                prism_project_id=body.prism_project_id,
            )
            db.add(link)
            await db.flush()
            created_links.append(link)
        except Exception:
            failed += 1
    await db.commit()
    return BulkGenerateResult(created=len(created_links), failed=failed, links=created_links)


@router.get("/", response_model=list[LinkOut])
async def list_links(
    product_id: Optional[str] = None,
    prism_project_id: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    from sqlalchemy import and_
    filters = [AffiliateLink.is_active == True]
    if product_id:
        filters.append(AffiliateLink.product_id == product_id)
    if prism_project_id:
        filters.append(AffiliateLink.prism_project_id == prism_project_id)

    result = await db.execute(
        select(AffiliateLink)
        .where(and_(*filters))
        .order_by(AffiliateLink.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return result.scalars().all()


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(
    link_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    link = await db.get(AffiliateLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link
