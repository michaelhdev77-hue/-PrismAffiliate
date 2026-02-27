"""
Admitad affiliate network adapter.

Auth: OAuth 2.0 client_credentials
Deeplink API: POST https://api.admitad.com/deeplink/{website_id}/advcampaign/{campaign_id}/
Product feeds: downloaded as YML/XML from Admitad CDN (no native product search).
Rate limits: 600 requests/min for deeplink API.

credentials dict:
{
    "client_id": "...",
    "client_secret": "...",
    "website_id": 12345,
    "campaign_id": 67890,       # Admitad campaign (offer) ID — per marketplace
    "access_token": "...",      # cached, auto-refreshed
    "token_expires_at": "..."   # ISO-8601
}
"""
from __future__ import annotations

import time
from typing import Optional

import httpx

from .base import (
    BaseMarketplaceAdapter,
    AffiliateLinkResult,
    ProductSearchResult,
    RateLimitInfo,
)


class AdmitadAdapter(BaseMarketplaceAdapter):
    BASE_URL = "https://api.admitad.com"
    TOKEN_URL = "https://api.admitad.com/token/"

    def search_products(
        self,
        query: str,
        credentials: dict,
        **kwargs,
    ) -> tuple[list[ProductSearchResult], RateLimitInfo]:
        # Admitad has no product search API.
        # Products come from YML/XML feeds downloaded by the worker.
        raise NotImplementedError(
            "Admitad does not provide product search. "
            "Use product feeds (FeedFormat.yml) via worker/tasks/feed_ingestion."
        )

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        token = self._get_token(credentials)
        website_id = credentials["website_id"]
        campaign_id = credentials["campaign_id"]

        params: dict = {"ulp": product_url}
        if sub_id:
            params["subid"] = sub_id

        resp = httpx.get(
            f"{self.BASE_URL}/deeplink/{website_id}/advcampaign/{campaign_id}/",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        affiliate_url = data[0]["link"] if isinstance(data, list) else data["link"]
        return AffiliateLinkResult(affiliate_url=affiliate_url)

    def fetch_feed(self, feed_url: str, credentials: dict) -> bytes:
        """Admitad feeds may require auth token in URL or as header."""
        token = self._get_token(credentials)
        resp = httpx.get(
            feed_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=300,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content

    def healthcheck(self, credentials: dict) -> dict:
        try:
            token = self._get_token(credentials)
            resp = httpx.get(
                f"{self.BASE_URL}/me/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return {"status": "ok", "account": resp.json().get("username")}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def _get_token(self, credentials: dict) -> str:
        expires_at = credentials.get("token_expires_at", 0)
        if expires_at and time.time() < float(expires_at) - 60:
            return credentials["access_token"]
        return self._refresh_token(credentials)

    def _refresh_token(self, credentials: dict) -> str:
        resp = httpx.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "scope": "deeplink_generator public_data",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        credentials["access_token"] = data["access_token"]
        credentials["token_expires_at"] = str(time.time() + data["expires_in"])
        return data["access_token"]
