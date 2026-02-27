"""Lightweight links-db models for the worker."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(36))
    marketplace: Mapped[str] = mapped_column(String(50))
    marketplace_account_id: Mapped[str] = mapped_column(String(36))
    affiliate_url: Mapped[str] = mapped_column(String(2048))
    short_code: Mapped[str] = mapped_column(String(20))
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
