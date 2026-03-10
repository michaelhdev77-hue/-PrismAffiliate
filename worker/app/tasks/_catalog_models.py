"""
Lightweight model definitions for the worker.
Worker accesses catalog-db directly for feed ingestion.
Mirrors catalog service models without FastAPI dependencies.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Boolean, DateTime, JSON, Integer, UniqueConstraint, Index, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class MarketplaceType(str, enum.Enum):
    amazon = "amazon"
    ebay = "ebay"
    aliexpress = "aliexpress"
    flipkart = "flipkart"
    walmart = "walmart"
    rakuten = "rakuten"
    yandex_market = "yandex_market"
    admitad = "admitad"
    gdeslon = "gdeslon"
    cj_affiliate = "cj_affiliate"
    impact = "impact"
    awin = "awin"


class FeedStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    syncing = "syncing"
    error = "error"


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    marketplace_account_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(255))
    external_campaign_id: Mapped[str] = mapped_column(String(100))
    marketplace_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketplaceAccount(Base):
    __tablename__ = "marketplace_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    marketplace: Mapped[str] = mapped_column(String(50))
    credentials_encrypted: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    health_status: Mapped[str] = mapped_column(String(50), default="unknown")
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    display_name: Mapped[str] = mapped_column(String(255), default="")


class ProductFeed(Base):
    __tablename__ = "product_feeds"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    marketplace_account_id: Mapped[str] = mapped_column(String(36))
    campaign_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    feed_format: Mapped[str] = mapped_column(SAEnum("yml", "xml", "csv", "json", "api", name="feedformat", create_type=False))
    feed_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    search_params: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule_cron: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(SAEnum("active", "paused", "syncing", "error", name="feedstatus", create_type=False), default="active")
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_products: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    niche_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marketplace: Mapped[str] = mapped_column(String(50))
    marketplace_account_id: Mapped[str] = mapped_column(String(36))
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(1000))
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String(255), default="")
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    image_url: Mapped[str] = mapped_column(String(2048), default="")
    product_url: Mapped[str] = mapped_column(String(2048))
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    commission_type: Mapped[str] = mapped_column(String(50), default="percentage")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    niche: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    feed_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("marketplace", "external_id", name="uq_marketplace_product"),
    )
