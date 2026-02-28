"""eBay Partner Network adapter (Browse API v1)."""
import base64
import time
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urljoin

import httpx

from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo

# eBay marketplace IDs and their Browse API base URLs
MARKETPLACE_ENDPOINTS: dict[str, str] = {
    "EBAY_US": "https://api.ebay.com",
    "EBAY_GB": "https://api.ebay.co.uk",
    "EBAY_DE": "https://api.ebay.de",
    "EBAY_AU": "https://api.ebay.com.au",
    "EBAY_CA": "https://api.ebay.ca",
    "EBAY_FR": "https://api.ebay.fr",
    "EBAY_IT": "https://api.ebay.it",
    "EBAY_ES": "https://api.ebay.es",
    "EBAY_IN": "https://api.ebay.in",
}

CURRENCY_BY_MARKETPLACE: dict[str, str] = {
    "EBAY_US": "USD", "EBAY_GB": "GBP", "EBAY_DE": "EUR",
    "EBAY_AU": "AUD", "EBAY_CA": "CAD", "EBAY_FR": "EUR",
    "EBAY_IT": "EUR", "EBAY_ES": "EUR", "EBAY_IN": "INR",
}


class EbayAdapter(BaseMarketplaceAdapter):
    """eBay Browse API + EPN (eBay Partner Network) adapter."""

    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_SCOPE = "https://api.ebay.com/oauth/api_scope"

    def _get_token(self, credentials: dict) -> str:
        now = time.time()
        expires_at = float(credentials.get("token_expires_at", 0))
        if credentials.get("access_token") and now < expires_at - 60:
            return credentials["access_token"]
        return self._refresh_token(credentials)

    def _refresh_token(self, credentials: dict) -> str:
        client_id = credentials["client_id"]
        client_secret = credentials["client_secret"]
        b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        resp = httpx.post(
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": self.BROWSE_SCOPE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        credentials["access_token"] = token
        credentials["token_expires_at"] = str(time.time() + data.get("expires_in", 7200))
        return token

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
        token = self._get_token(credentials)
        marketplace_id = credentials.get("marketplace_id", "EBAY_US")
        campaign_id = credentials.get("campaign_id", "")
        base_url = MARKETPLACE_ENDPOINTS.get(marketplace_id, MARKETPLACE_ENDPOINTS["EBAY_US"])

        sort_map = {"price": "price", "rating": "bestMatch", "newest": "newlyListed"}
        ebay_sort = sort_map.get(sort_by, "bestMatch")

        filters = []
        if min_price is not None or max_price is not None:
            lo = int(min_price * 100) if min_price else ""
            hi = int(max_price * 100) if max_price else ""
            filters.append(f"price:[{lo}..{hi}]")
            filters.append(f"priceCurrency:{CURRENCY_BY_MARKETPLACE.get(marketplace_id, 'USD')}")

        params: dict = {
            "q": query,
            "limit": min(page_size, 200),
            "offset": (page - 1) * page_size,
            "sort": ebay_sort,
        }
        if category:
            params["category_ids"] = category
        if filters:
            params["filter"] = ",".join(filters)

        resp = httpx.get(
            f"{base_url}/buy/browse/v1/item_summary/search",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": marketplace_id,
                "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={campaign_id}",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        results = [self._parse_item(item) for item in data.get("itemSummaries", [])]

        remaining = int(resp.headers.get("x-ebay-c-ratelimit-remaining", -1))
        limit_val = int(resp.headers.get("x-ebay-c-ratelimit-limit", 5000))
        rate = RateLimitInfo(
            requests_remaining=remaining if remaining >= 0 else limit_val,
            requests_limit=limit_val,
        )
        return results, rate

    def _parse_item(self, item: dict) -> ProductSearchResult:
        price_info = item.get("price", {})
        price = float(price_info.get("value", 0))
        currency = price_info.get("currency", "USD")

        # Use affiliate URL if available (requires campaign_id in request header)
        affiliate_url = item.get("itemAffiliateWebUrl") or item.get("itemWebUrl", "")

        return ProductSearchResult(
            external_id=item.get("itemId", ""),
            title=item.get("title", ""),
            description="",
            category=item.get("categories", [{}])[0].get("categoryName", "") if item.get("categories") else "",
            price=price,
            currency=currency,
            image_url=(item.get("image") or {}).get("imageUrl", ""),
            product_url=affiliate_url,
            in_stock=item.get("itemLocation") is not None,
            commission_rate=0.0,  # eBay does not expose per-item commission
            commission_type="percentage",
            brand=(item.get("seller") or {}).get("username", ""),
            rating=None,
            review_count=None,
            raw_data=item,
        )

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        """Append EPN tracking params to an eBay item URL."""
        campaign_id = credentials.get("campaign_id", "")
        sep = "&" if "?" in product_url else "?"
        params = f"mkevt=1&mkcid=1&mkrid=711-53200-19255-0&campid={campaign_id}&toolid=10001"
        if sub_id:
            params += f"&customid={sub_id}"
        return AffiliateLinkResult(
            affiliate_url=f"{product_url}{sep}{params}",
            tracking_params={"campaign_id": campaign_id, "sub_id": sub_id},
        )

    def healthcheck(self, credentials: dict) -> dict:
        try:
            self._refresh_token(credentials)
            marketplace_id = credentials.get("marketplace_id", "EBAY_US")
            return {"status": "ok", "marketplace": marketplace_id}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
