from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import require_auth
from app.models import ProductFeed, FeedFormat, FeedStatus

router = APIRouter()


class FeedCreate(BaseModel):
    marketplace_account_id: str
    name: str
    feed_format: FeedFormat
    feed_url: Optional[str] = None
    search_params: dict = {}
    schedule_cron: str = "0 */6 * * *"
    category_mapping: dict = {}
    niche_mapping: dict = {}


class FeedUpdate(BaseModel):
    name: Optional[str] = None
    feed_url: Optional[str] = None
    search_params: Optional[dict] = None
    schedule_cron: Optional[str] = None
    status: Optional[FeedStatus] = None
    category_mapping: Optional[dict] = None
    niche_mapping: Optional[dict] = None


class FeedOut(BaseModel):
    id: str
    marketplace_account_id: str
    name: str
    feed_format: FeedFormat
    feed_url: Optional[str]
    search_params: dict
    schedule_cron: str
    status: FeedStatus
    last_sync_at: Optional[datetime]
    last_sync_products: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[FeedOut])
async def list_feeds(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    result = await db.execute(select(ProductFeed).order_by(ProductFeed.created_at))
    return result.scalars().all()


@router.post("/", response_model=FeedOut, status_code=status.HTTP_201_CREATED)
async def create_feed(
    body: FeedCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    feed = ProductFeed(**body.model_dump())
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return feed


@router.get("/{feed_id}", response_model=FeedOut)
async def get_feed(
    feed_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    feed = await db.get(ProductFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    return feed


@router.patch("/{feed_id}", response_model=FeedOut)
async def update_feed(
    feed_id: str,
    body: FeedUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    feed = await db.get(ProductFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(feed, field, value)
    await db.commit()
    await db.refresh(feed)
    return feed


@router.delete("/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    feed = await db.get(ProductFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    await db.delete(feed)
    await db.commit()


@router.post("/{feed_id}/sync")
async def trigger_sync(
    feed_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    feed = await db.get(ProductFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    # Worker picks this up via Celery — here we just mark it
    feed.status = FeedStatus.syncing
    await db.commit()
    return {"status": "sync_queued", "feed_id": feed_id}
