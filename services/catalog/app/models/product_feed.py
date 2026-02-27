import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Integer, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FeedFormat(str, enum.Enum):
    yml = "yml"
    xml = "xml"
    csv = "csv"
    json_feed = "json"
    api = "api"


class FeedStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    syncing = "syncing"
    error = "error"


class ProductFeed(Base):
    __tablename__ = "product_feeds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marketplace_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    feed_format: Mapped[FeedFormat] = mapped_column(SAEnum(FeedFormat), nullable=False)
    feed_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    search_params: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule_cron: Mapped[str] = mapped_column(String(100), default="0 */6 * * *")
    status: Mapped[FeedStatus] = mapped_column(SAEnum(FeedStatus), default=FeedStatus.active)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_products: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    niche_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
