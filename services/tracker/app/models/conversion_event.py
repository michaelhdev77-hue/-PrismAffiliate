import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    affiliate_link_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_account_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    order_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    order_amount: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    conversion_status: Mapped[str] = mapped_column(String(50), default="pending")
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
