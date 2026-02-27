"""
Generates affiliate links by calling the Catalog service for product info,
then calling the appropriate marketplace adapter.
"""
from __future__ import annotations

import string
import random
from typing import Optional

import httpx

from shared.adapters import get_adapter
from shared.encryption import decrypt_json


def generate_short_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=length))


async def generate_link_for_product(
    product_id: str,
    catalog_url: str,
    encryption_key: str,
    sub_id: Optional[str] = None,
) -> dict:
    """
    Fetch product info from catalog, get credentials for its marketplace account,
    call the adapter to generate an affiliate URL.
    Returns dict with affiliate_url, short_code, marketplace, expires_at.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        product_resp = await client.get(f"{catalog_url}/internal/products/{product_id}/summary")
        product_resp.raise_for_status()
        product = product_resp.json()

        # Fetch marketplace account credentials from catalog
        accounts_resp = await client.get(f"{catalog_url}/internal/account-for-product/{product_id}")
        accounts_resp.raise_for_status()
        account = accounts_resp.json()

    credentials = decrypt_json(account["credentials_encrypted"], encryption_key)
    adapter = get_adapter(product["marketplace"])
    result = adapter.generate_affiliate_link(
        product_url=product["product_url"],
        credentials=credentials,
        sub_id=sub_id,
    )

    return {
        "affiliate_url": result.affiliate_url,
        "short_code": generate_short_code(),
        "marketplace": product["marketplace"],
        "marketplace_account_id": account["id"],
        "expires_at": result.expires_at,
    }
