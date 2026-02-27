"""
GdeSlon affiliate network adapter (Russia).

Unified product search across ~400 RU shops.
Search API: GET https://www.gdeslon.ru/api/search.xml
Returns Yandex Market Language (YML) XML.

credentials dict:
{
    "api_key": "...",       # _gs_at parameter
    "affiliate_id": "..."   # optional tracking ID
}
"""
from __future__ import annotations

from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from .base import (
    BaseMarketplaceAdapter,
    AffiliateLinkResult,
    ProductSearchResult,
    RateLimitInfo,
)


class GdeSlonAdapter(BaseMarketplaceAdapter):
    BASE_URL = "https://www.gdeslon.ru/api"

    def search_products(
        self,
        query: str,
        credentials: dict,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProductSearchResult], RateLimitInfo]:
        params: dict = {
            "q": query,
            "_gs_at": credentials["api_key"],
            "l": min(page_size, 100),
            "p": page - 1,  # GdeSlon uses 0-based pages
        }
        if category:
            params["m"] = category
        if sort_by == "price":
            params["order"] = "price"
        elif sort_by == "commission":
            params["order"] = "partner_benefit"

        resp = httpx.get(
            f"{self.BASE_URL}/search.xml",
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        results = self._parse_yml_response(resp.content)
        return results, RateLimitInfo()

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        # GdeSlon embeds affiliate links directly in search results.
        # For external URLs, we append the affiliate ID as a query param.
        affiliate_id = credentials.get("affiliate_id", "")
        url = product_url
        if affiliate_id:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}_gs_at={affiliate_id}"
        return AffiliateLinkResult(affiliate_url=url)

    def healthcheck(self, credentials: dict) -> dict:
        try:
            resp = httpx.get(
                f"{self.BASE_URL}/users/shops.xml",
                params={"_gs_at": credentials["api_key"], "l": 1},
                timeout=10,
            )
            resp.raise_for_status()
            return {"status": "ok"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def _parse_yml_response(self, raw: bytes) -> list[ProductSearchResult]:
        results = []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return results

        shop = root.find("shop")
        if shop is None:
            return results

        currencies: dict[str, float] = {}
        for cur in shop.findall("currencies/currency"):
            currencies[cur.get("id", "")] = float(cur.get("rate", 1))

        categories: dict[str, str] = {}
        for cat in shop.findall("categories/category"):
            categories[cat.get("id", "")] = cat.text or ""

        for offer in shop.findall("offers/offer"):
            try:
                price_raw = float(offer.findtext("price") or 0)
                currency_id = offer.findtext("currencyId") or "RUB"
                cat_id = offer.findtext("categoryId") or ""
                results.append(
                    ProductSearchResult(
                        external_id=offer.get("id", ""),
                        title=offer.findtext("name") or offer.findtext("model") or "",
                        description=offer.findtext("description") or "",
                        category=categories.get(cat_id, cat_id),
                        price=price_raw,
                        currency=currency_id,
                        image_url=offer.findtext("picture") or "",
                        product_url=offer.findtext("url") or "",
                        in_stock=offer.get("available", "true").lower() != "false",
                        commission_rate=float(offer.findtext("sales_notes") or 0),
                        commission_type="percentage",
                        brand=offer.findtext("vendor"),
                        tags=[
                            t.text for t in offer.findall("param")
                            if t.text
                        ],
                        raw_data={"yml_offer_id": offer.get("id")},
                    )
                )
            except (ValueError, TypeError):
                continue
        return results
