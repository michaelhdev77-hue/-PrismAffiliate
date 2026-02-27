"""
Click tracking and redirect endpoint.
GET /r/{short_code} → records click → 302 to affiliate URL.
"""
import hashlib
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db import get_db
from app.models import ClickEvent
from app.config import settings

router = APIRouter()


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


@router.get("/r/{short_code}")
async def click_redirect(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Resolve short_code → affiliate_url via links service
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.links_service_url}/internal/links/resolve/{short_code}"
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return Response(status_code=404, content="Link not found")

    affiliate_url = data["affiliate_url"]
    product_id = data["product_id"]

    # 2. Record click event (fire and forget — don't block redirect)
    ip = request.client.host if request.client else "unknown"
    click = ClickEvent(
        short_code=short_code,
        product_id=product_id,
        marketplace=data.get("marketplace", ""),
        ip_hash=_hash_ip(ip),
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )
    db.add(click)
    await db.commit()

    return RedirectResponse(url=affiliate_url, status_code=302)
