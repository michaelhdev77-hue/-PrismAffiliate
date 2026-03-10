"""
Conversion webhook receivers — called by marketplace/network postback URLs.
Each marketplace has a different payload format.
"""
import uuid
import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import ConversionEvent

logger = logging.getLogger(__name__)

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

    # Resolve subid to get product and PRISM context
    if payload.subid:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://links:8012/internal/links/by-subid/{payload.subid}")
                if resp.status_code == 200:
                    link_data = resp.json()
                    event.affiliate_link_id = link_data.get("id")
                    event.product_id = link_data.get("product_id")
                    event.prism_content_id = link_data.get("prism_content_id")
                    event.prism_project_id = link_data.get("prism_project_id")
                    event.marketplace_account_id = link_data.get("marketplace_account_id")
        except Exception as exc:
            logger.warning("Failed to resolve subid %s: %s", payload.subid, exc)

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
