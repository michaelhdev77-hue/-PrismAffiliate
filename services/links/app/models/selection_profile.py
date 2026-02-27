import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, JSON, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SelectionProfile(Base):
    __tablename__ = "selection_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prism_project_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    marketplaces: Mapped[list] = mapped_column(JSON, default=list)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    min_commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    min_rating: Mapped[float] = mapped_column(Float, default=0.0)
    min_review_count: Mapped[int] = mapped_column(Integer, default=0)
    price_range_min: Mapped[float] = mapped_column(Float, default=0.0)
    price_range_max: Mapped[float] = mapped_column(Float, default=0.0)
    sort_by: Mapped[str] = mapped_column(String(50), default="commission")
    max_products: Mapped[int] = mapped_column(Integer, default=5)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
