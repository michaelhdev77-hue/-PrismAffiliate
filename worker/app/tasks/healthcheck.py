"""Periodic healthcheck of all active marketplace accounts."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="affiliate.healthcheck_accounts")
def healthcheck_accounts():
    asyncio.run(_healthcheck_all())


async def _healthcheck_all():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.catalog_service_url}/api/v1/marketplace-accounts/",
            # Internal call — no auth needed for healthcheck trigger
        )
        if resp.status_code != 200:
            logger.error("Failed to list accounts for healthcheck")
            return
        accounts = resp.json()

    for account in accounts:
        if not account.get("is_active"):
            continue
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"{settings.catalog_service_url}/api/v1/marketplace-accounts/{account['id']}/healthcheck",
                )
        except Exception as exc:
            logger.error(f"Healthcheck failed for account {account['id']}: {exc}")
