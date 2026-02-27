"""
Amazon Associates adapter — Amazon Creators API.

Note: Amazon PA-API 5.0 is deprecated as of May 2026.
This adapter targets the Creators API (successor).

Docs: https://affiliate-program.amazon.com/creatorsapi/docs/en-us/introduction
Auth: OAuth 2.0 client_credentials

credentials dict:
{
    "credential_id": "...",       # from Associates Central
    "credential_secret": "...",
    "partner_tag": "mystore-20",  # Associates tracking tag
    "marketplace": "www.amazon.com",  # or amazon.co.uk, amazon.de, etc.
    "access_token": "...",        # cached
    "token_expires_at": "..."
}

Rate limits: 1 TPS / 8640 requests per day (scales with revenue).
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


class AmazonAdapter(BaseMarketplaceAdapter):
    AUTH_URL = "https://api.amazon.com/auth/o2/token"

    # Per-marketplace API endpoints
    API_ENDPOINTS = {
        "www.amazon.com": "https://webservices.amazon.com",
        "www.amazon.co.uk": "https://webservices.amazon.co.uk",
        "www.amazon.de": "https://webservices.amazon.de",
        "www.amazon.co.jp": "https://webservices.amazon.co.jp",
        "www.amazon.in": "https://webservices.amazon.in",
        "www.amazon.fr": "https://webservices.amazon.fr",
        "www.amazon.es": "https://webservices.amazon.es",
        "www.amazon.it": "https://webservices.amazon.it",
        "www.amazon.ca": "https://webservices.amazon.ca",
    }

    def search_products(
        self,
        query: str,
        credentials: dict,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ProductSearchResult], RateLimitInfo]:
        token = self._get_token(credentials)
        marketplace = credentials.get("marketplace", "www.amazon.com")
        base = self.API_ENDPOINTS.get(marketplace, self.API_ENDPOINTS["www.amazon.com"])

        payload: dict = {
            "Keywords": query,
            "PartnerTag": credentials["partner_tag"],
            "PartnerType": "Associates",
            "Resources": [
                "ItemInfo.Title",
                "ItemInfo.ByLineInfo",
                "Offers.Listings.Price",
                "Images.Primary.Large",
                "CustomerReviews.StarRating",
                "CustomerReviews.Count",
                "BrowseNodeInfo.BrowseNodes",
            ],
            "ItemCount": min(page_size, 10),
            "ItemPage": page,
        }
        if category:
            payload["SearchIndex"] = category
        if sort_by == "price":
            payload["SortBy"] = "Price:LowToHigh"
        elif sort_by == "rating":
            payload["SortBy"] = "AvgCustomerReviews"
        if min_price is not None:
            payload["MinPrice"] = int(min_price * 100)
        if max_price is not None:
            payload["MaxPrice"] = int(max_price * 100)

        resp = httpx.post(
            f"{base}/paapi5/searchitems",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
            },
            timeout=15,
        )

        rate_info = RateLimitInfo(
            requests_remaining=int(resp.headers.get("x-amzn-RateLimit-Remaining", -1)),
            requests_limit=int(resp.headers.get("x-amzn-RateLimit-Limit", -1)),
        )

        resp.raise_for_status()
        data = resp.json()
        results = [
            self._parse_item(item, credentials["partner_tag"])
            for item in data.get("SearchResult", {}).get("Items", [])
        ]
        return results, rate_info

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        tag = credentials["partner_tag"]
        sep = "&" if "?" in product_url else "?"
        url = f"{product_url}{sep}tag={tag}"
        if sub_id:
            url += f"&linkCode=as2&creative=9325&creativeASIN={sub_id}"
        return AffiliateLinkResult(affiliate_url=url)

    def healthcheck(self, credentials: dict) -> dict:
        try:
            self._get_token(credentials)
            return {"status": "ok", "partner_tag": credentials.get("partner_tag")}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def _get_token(self, credentials: dict) -> str:
        expires_at = credentials.get("token_expires_at", 0)
        if expires_at and time.time() < float(expires_at) - 60:
            return credentials["access_token"]
        return self._refresh_token(credentials)

    def _refresh_token(self, credentials: dict) -> str:
        resp = httpx.post(
            self.AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": credentials["credential_id"],
                "client_secret": credentials["credential_secret"],
                "scope": "advertising::manage",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        credentials["access_token"] = data["access_token"]
        credentials["token_expires_at"] = str(time.time() + data["expires_in"])
        return data["access_token"]

    def _parse_item(self, item: dict, partner_tag: str) -> ProductSearchResult:
        info = item.get("ItemInfo", {})
        offers = item.get("Offers", {}).get("Listings", [{}])
        listing = offers[0] if offers else {}
        price_data = listing.get("Price", {})
        images = item.get("Images", {}).get("Primary", {}).get("Large", {})
        reviews = item.get("CustomerReviews", {})
        nodes = item.get("BrowseNodeInfo", {}).get("BrowseNodes", [{}])

        asin = item.get("ASIN", "")
        detail_url = item.get("DetailPageURL", f"https://www.amazon.com/dp/{asin}")
        affiliate_url = f"{detail_url}{'&' if '?' in detail_url else '?'}tag={partner_tag}"

        return ProductSearchResult(
            external_id=asin,
            title=info.get("Title", {}).get("DisplayValue", ""),
            description="",
            category=nodes[0].get("DisplayName", "") if nodes else "",
            brand=info.get("ByLineInfo", {}).get("Brand", {}).get("DisplayValue"),
            price=price_data.get("Amount", 0.0),
            currency=price_data.get("Currency", "USD"),
            image_url=images.get("URL", ""),
            product_url=affiliate_url,
            in_stock=listing.get("Availability", {}).get("Type", "") == "Now",
            commission_rate=0.0,  # Amazon doesn't expose commission per item
            commission_type="percentage",
            rating=reviews.get("StarRating", {}).get("Value"),
            review_count=reviews.get("Count"),
            tags=[n.get("DisplayName", "") for n in nodes if n.get("DisplayName")],
            raw_data={"asin": asin},
        )
