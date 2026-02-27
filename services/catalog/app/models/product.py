import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Float, Boolean, DateTime, JSON, Integer,
    UniqueConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)

    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    image_url: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    product_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)

    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    commission_type: Mapped[str] = mapped_column(String(50), default="percentage")

    tags: Mapped[list] = mapped_column(JSON, default=list)
    niche: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    feed_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("marketplace", "external_id", name="uq_marketplace_product"),
        Index("ix_products_category", "category"),
        Index("ix_products_commission_rate", "commission_rate"),
        Index("ix_products_marketplace_active", "marketplace", "is_active"),
    )
