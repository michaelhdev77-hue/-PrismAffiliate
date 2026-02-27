import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, JSON, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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


class MarketplaceAccount(Base):
    __tablename__ = "marketplace_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marketplace: Mapped[MarketplaceType] = mapped_column(SAEnum(MarketplaceType), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    health_status: Mapped[str] = mapped_column(String(50), default="unknown")
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
