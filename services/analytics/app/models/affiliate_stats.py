import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, Date, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AffiliateStats(Base):
    __tablename__ = "affiliate_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "stat_date", "marketplace", "product_id", "prism_project_id", "prism_content_id",
            name="uq_daily_stats",
        ),
    )
