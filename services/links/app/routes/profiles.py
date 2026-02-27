from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import SelectionProfile

router = APIRouter()


class ProfileCreate(BaseModel):
    prism_project_id: str
    name: str
    marketplaces: list[str] = []
    categories: list[str] = []
    keywords: list[str] = []
    min_commission_rate: float = 0.0
    min_rating: float = 0.0
    min_review_count: int = 0
    price_range_min: float = 0.0
    price_range_max: float = 0.0
    sort_by: str = "commission"
    max_products: int = 5


class ProfileOut(BaseModel):
    id: str
    prism_project_id: str
    name: str
    marketplaces: list
    categories: list
    keywords: list
    min_commission_rate: float
    min_rating: float
    min_review_count: int
    price_range_min: float
    price_range_max: float
    sort_by: str
    max_products: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ProfileOut])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(SelectionProfile))
    return result.scalars().all()


@router.post("/", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = SelectionProfile(**body.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = await db.get(SelectionProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: str,
    body: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = await db.get(SelectionProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for field, value in body.model_dump().items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = await db.get(SelectionProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()
