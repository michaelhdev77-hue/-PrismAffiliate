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

    def list_programs(self, credentials: dict, website_id: str) -> list[dict]:
        """
        List ALL connected programs for the website.
        GET /advcampaigns/website/{website_id}/?connection_status=active
        """
        token = self._get_token(credentials)
        programs = []
        offset = 0
        limit = 50
        while True:
            resp = httpx.get(
                f"{self.BASE_URL}/advcampaigns/website/{website_id}/",
                params={
                    "limit": limit,
                    "offset": offset,
                    "connection_status": "active",
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", []) if isinstance(data, dict) else data
            if not results:
                break
            for p in (results if isinstance(results, list) else [results]):
                programs.append({
                    "id": str(p.get("id", "")),
                    "name": p.get("name", ""),
                    "status": p.get("connection_status", p.get("status", "")),
                    "currency": p.get("currency", ""),
                    "categories": [c.get("name", "") for c in p.get("categories", [])],
                    "avg_money_transfer_time": p.get("avg_money_transfer_time"),
                    "cr": p.get("cr"),
                    "ecpc": p.get("ecpc"),
                })
            if len(results) < limit:
                break
            offset += limit
        return programs

    def fetch_program_feeds(self, credentials: dict, website_id: str) -> list[dict]:
        """
        Fetch available product feeds for all programs connected to the website.
        GET /advcampaigns/website/{website_id}/
        """
        token = self._get_token(credentials)
        feeds = []
        offset = 0
        limit = 20
        while True:
            resp = httpx.get(
                f"{self.BASE_URL}/advcampaigns/website/{website_id}/",
                params={"limit": limit, "offset": offset},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            if not results:
                break
            for program in (results if isinstance(results, list) else [results]):
                feeds_info = program.get("feeds_info") or []
                if not isinstance(feeds_info, list):
                    feeds_info = []
                for fi in feeds_info:
                    xml_link = fi.get("xml_link", "")
                    csv_link = fi.get("csv_link", "")
                    if xml_link or csv_link:
                        feeds.append({
                            "name": fi.get("name", program.get("name", "")),
                            "xml_link": xml_link,
                            "csv_link": csv_link,
                            "campaign_name": program.get("name", ""),
                            "campaign_id": str(program.get("id", "")),
                        })
            if len(results) < limit:
                break
            offset += limit
        return feeds

    def healthcheck(self, credentials: dict) -> dict:
        try:
            token = self._get_token(credentials)
            website_id = credentials["website_id"]
            resp = httpx.get(
                f"{self.BASE_URL}/websites/{website_id}/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"status": "ok", "website": data.get("name"), "website_id": website_id}
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
                "scope": "deeplink_generator public_data websites advcampaigns advcampaigns_for_website",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        credentials["access_token"] = data["access_token"]
        credentials["token_expires_at"] = str(time.time() + data["expires_in"])
        return data["access_token"]
