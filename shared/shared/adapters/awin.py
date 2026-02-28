"""Awin (Affiliate Window) adapter — Link Builder API + product data feeds."""
from typing import Optional
from urllib.parse import quote_plus

import httpx

from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo


class AwinAdapter(BaseMarketplaceAdapter):
    """Awin publisher adapter.

    Awin does not provide a live product search API — products are distributed
    via CSV/JSONL data feeds downloaded from productdata.awin.com.
    This adapter handles affiliate link generation and feed downloads.

    Credentials:
        api_token: str          — OAuth2 Bearer token (from Awin publisher account)
        publisher_id: str       — your Awin publisher/affiliate ID
        datafeed_api_key: str   — for downloading product data feeds (Toolbox > Create-a-Feed)
    """

    API_BASE = "https://api.awin.com"
    FEED_BASE = "https://productdata.awin.com/datafeed/list/apikey"
    LINK_BUILDER_URL = "https://api.awin.com/publishers/{publisher_id}/linkbuilder/generate"
    SIMPLE_LINK_BASE = "https://www.awin1.com/cread.php"

    def search_products(
        self,
        query: str,
        credentials: dict,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProductSearchResult], RateLimitInfo]:
        raise NotImplementedError(
            "Awin does not support live product search. "
            "Use product data feeds (fetch_feed) to index products locally."
        )

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        """Generate an Awin affiliate link via the Link Builder API.

        Falls back to constructing the URL manually if advertiser_id is not provided.
        """
        publisher_id = credentials["publisher_id"]
        advertiser_id = credentials.get("advertiser_id")  # optional, set per-product if known

        if advertiser_id:
            return self._api_link(publisher_id, advertiser_id, product_url, credentials, sub_id)
        else:
            return self._simple_link(publisher_id, product_url, sub_id)

    def _api_link(
        self,
        publisher_id: str,
        advertiser_id: str,
        destination_url: str,
        credentials: dict,
        sub_id: Optional[str],
    ) -> AffiliateLinkResult:
        token = credentials["api_token"]
        body: dict = {
            "advertiserId": int(advertiser_id),
            "destinationUrl": destination_url,
            "parameters": {},
        }
        if sub_id:
            body["parameters"]["clickref"] = sub_id

        try:
            resp = httpx.post(
                self.LINK_BUILDER_URL.format(publisher_id=publisher_id),
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return AffiliateLinkResult(
                affiliate_url=data["url"],
                tracking_params={"publisher_id": publisher_id, "advertiser_id": advertiser_id},
            )
        except httpx.HTTPStatusError:
            # Advertiser may not allow deep linking — fall back to simple link
            return self._simple_link(publisher_id, destination_url, sub_id)

    def _simple_link(
        self,
        publisher_id: str,
        destination_url: str,
        sub_id: Optional[str],
    ) -> AffiliateLinkResult:
        """Construct Awin affiliate URL without API call."""
        encoded = quote_plus(destination_url)
        url = f"{self.SIMPLE_LINK_BASE}?awinaffid={publisher_id}&ued={encoded}"
        if sub_id:
            url += f"&clickref={sub_id}"
        return AffiliateLinkResult(
            affiliate_url=url,
            tracking_params={"publisher_id": publisher_id, "sub_id": sub_id},
        )

    def fetch_feed(self, feed_url: str, credentials: dict) -> bytes:
        """Download an Awin product data feed.

        feed_url can be a full productdata.awin.com URL or just an advertiser feed URL.
        The datafeed_api_key is embedded in the URL path for productdata.awin.com feeds.
        """
        datafeed_api_key = credentials.get("datafeed_api_key", "")
        # If a bare advertiser ID is given, construct the standard feed URL
        if feed_url.isdigit():
            feed_url = f"{self.FEED_BASE}/{datafeed_api_key}/{feed_url}"

        resp = httpx.get(
            feed_url,
            headers={"Authorization": f"Bearer {credentials.get('api_token', '')}"},
            timeout=300,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content

    def healthcheck(self, credentials: dict) -> dict:
        try:
            token = credentials["api_token"]
            publisher_id = credentials["publisher_id"]
            resp = httpx.get(
                f"{self.API_BASE}/publishers/{publisher_id}/programmes",
                params={"relationship": "joined"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            count = len(data) if isinstance(data, list) else 0
            return {"status": "ok", "publisher_id": publisher_id, "joined_programmes": count}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
