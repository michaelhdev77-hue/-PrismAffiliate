"""Lightweight tracker-db models for the worker."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    pass


class ClickEvent(Base):
    __tablename__ = "click_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    short_code: Mapped[str] = mapped_column(String(20))
    affiliate_link_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    product_id: Mapped[str] = mapped_column(String(36))
    marketplace: Mapped[str] = mapped_column(String(50))
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ip_hash: Mapped[str] = mapped_column(String(64))
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversionEvent(Base):
    __tablename__ = "conversion_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    affiliate_link_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    marketplace: Mapped[str] = mapped_column(String(50))
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    order_id: Mapped[str] = mapped_column(String(255))
    order_amount: Mapped[float] = mapped_column(Float)
    commission_amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10))
    conversion_status: Mapped[str] = mapped_column(String(50))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
