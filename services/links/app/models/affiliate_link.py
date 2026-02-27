import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    marketplace_account_id: Mapped[str] = mapped_column(String(36), nullable=False)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    short_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # PRISM integration
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
