"""CJ Affiliate (Commission Junction) adapter — REST Product Search API v2."""
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlencode, quote_plus

import httpx

from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo


class CJAffiliateAdapter(BaseMarketplaceAdapter):
    """CJ Affiliate product search + deep link adapter.

    Credentials:
        personal_access_token: str  — from developers.cj.com (long-lived)
        website_id: str             — your CJ publisher website/property ID
        company_id: str             — your CJ CID (visible in dashboard)
    """

    SEARCH_URL = "https://product-search.api.cj.com/v2/product-search"

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
        token = credentials["personal_access_token"]
        website_id = credentials["website_id"]

        sort_map = {
            "price": "price",
            "commission": "sale-price",
            "newest": "name",
            "relevance": "relevance",
        }

        params: dict = {
            "website-id": website_id,
            "advertiser-ids": "joined",
            "keywords": query,
            "records-per-page": min(page_size, 100),
            "page-number": page,
            "sort-by": sort_map.get(sort_by, "relevance"),
            "sort-order": "desc",
        }
        if min_price is not None:
            params["low-price"] = str(min_price)
        if max_price is not None:
            params["high-price"] = str(max_price)

        resp = httpx.get(
            self.SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        resp.raise_for_status()

        results = self._parse_xml(resp.content)
        rate = RateLimitInfo(requests_remaining=-1, requests_limit=-1)
        return results, rate

    def _parse_xml(self, raw: bytes) -> list[ProductSearchResult]:
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []

        products_el = root.find("products")
        if products_el is None:
            return []

        results = []
        for p in products_el.findall("product"):
            def t(tag: str) -> str:
                el = p.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            price_str = t("price") or t("sale-price") or "0"
            orig_price_str = t("price") if t("sale-price") else ""

            try:
                price = float(price_str)
            except ValueError:
                price = 0.0

            try:
                orig_price = float(orig_price_str) if orig_price_str else None
            except ValueError:
                orig_price = None

            # buy-url already contains affiliate tracking
            affiliate_url = t("buy-url")
            product_url = t("instock-url") or affiliate_url

            results.append(ProductSearchResult(
                external_id=t("ad-id") or t("sku"),
                title=t("name"),
                description=t("description"),
                category=t("category"),
                price=price,
                currency=t("currency") or "USD",
                image_url=t("image-url"),
                product_url=affiliate_url or product_url,
                in_stock=True,
                commission_rate=0.0,  # CJ does not expose per-item commission in search
                commission_type="percentage",
                brand=t("manufacturer-name"),
                original_price=orig_price,
                raw_data={el.tag: el.text for el in p},
            ))
        return results

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        """CJ buy-urls are already affiliate links; for arbitrary URLs construct a deeplink.

        Note: CJ does not offer a standalone deep link API — advertisers must enable it.
        We append the website-id as a sub-id to the URL, which some CJ advertisers support.
        """
        website_id = credentials.get("website_id", "")
        # Standard CJ deep link pattern (works when advertiser allows deep linking)
        encoded = quote_plus(product_url)
        affiliate_url = (
            f"https://www.anrdoezrs.net/click-{website_id}-10449897"
            f"?url={encoded}"
            + (f"&sid={sub_id}" if sub_id else "")
        )
        return AffiliateLinkResult(
            affiliate_url=affiliate_url,
            tracking_params={"website_id": website_id, "sub_id": sub_id},
        )

    def healthcheck(self, credentials: dict) -> dict:
        try:
            token = credentials["personal_access_token"]
            website_id = credentials["website_id"]
            resp = httpx.get(
                self.SEARCH_URL,
                params={
                    "website-id": website_id,
                    "advertiser-ids": "joined",
                    "keywords": "test",
                    "records-per-page": "1",
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return {"status": "ok", "website_id": website_id}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
