"""
Conversion webhook receivers — called by marketplace/network postback URLs.
Each marketplace has a different payload format.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ConversionEvent

router = APIRouter()


class AdmitadPostback(BaseModel):
    order_id: str
    advcampaign_id: Optional[str] = None
    order_sum: Optional[float] = None
    payment_sum: Optional[float] = None
    currency: Optional[str] = "RUB"
    action: Optional[str] = "sale"
    subid: Optional[str] = None


@router.post("/webhooks/admitad")
async def admitad_postback(
    payload: AdmitadPostback,
    db: AsyncSession = Depends(get_db),
):
    event = ConversionEvent(
        marketplace="admitad",
        order_id=payload.order_id,
        order_amount=payload.order_sum or 0.0,
        commission_amount=payload.payment_sum or 0.0,
        currency=payload.currency or "RUB",
        conversion_status="pending",
        converted_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    return {"status": "ok"}


@router.post("/webhooks/amazon")
async def amazon_postback(request: Request, db: AsyncSession = Depends(get_db)):
    """Amazon SNS / Associates API conversion notification."""
    body = await request.json()
    event = ConversionEvent(
        marketplace="amazon",
        order_id=body.get("orderId", str(uuid.uuid4())),
        order_amount=float(body.get("orderTotal", 0)),
        commission_amount=float(body.get("commission", 0)),
        currency=body.get("currency", "USD"),
        conversion_status="pending",
        converted_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    return {"status": "ok"}


@router.post("/webhooks/{marketplace}")
async def generic_postback(
    marketplace: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Catch-all for other marketplaces — store raw payload."""
    body = await request.json()
    event = ConversionEvent(
        marketplace=marketplace,
        order_id=body.get("order_id", str(uuid.uuid4())),
        order_amount=float(body.get("amount", 0)),
        commission_amount=float(body.get("commission", 0)),
        currency=body.get("currency", "USD"),
        conversion_status="pending",
        converted_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    return {"status": "ok"}
