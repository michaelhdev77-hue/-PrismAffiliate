from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import Campaign, MarketplaceAccount

router = APIRouter()


class CampaignCreate(BaseModel):
    marketplace_account_id: str
    name: str
    external_campaign_id: str
    marketplace_label: Optional[str] = None
    config: dict = {}


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    external_campaign_id: Optional[str] = None
    marketplace_label: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class CampaignOut(BaseModel):
    id: str
    marketplace_account_id: str
    name: str
    external_campaign_id: str
    marketplace_label: Optional[str]
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[CampaignOut])
async def list_campaigns(
    marketplace_account_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    stmt = select(Campaign).order_by(Campaign.created_at)
    if marketplace_account_id:
        stmt = stmt.where(Campaign.marketplace_account_id == marketplace_account_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    account = await db.get(MarketplaceAccount, body.marketplace_account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Marketplace account not found")
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    await db.commit()
