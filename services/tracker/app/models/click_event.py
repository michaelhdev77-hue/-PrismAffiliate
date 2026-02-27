import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    short_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    affiliate_link_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    prism_content_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prism_project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_clicks_time", "clicked_at"),
        Index("ix_clicks_product_time", "product_id", "clicked_at"),
    )
