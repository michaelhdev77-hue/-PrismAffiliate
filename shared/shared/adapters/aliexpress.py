"""
AliExpress Affiliate adapter — AliExpress Open Platform API.

Docs: https://developers.aliexpress.com/en/doc.htm
API gateway: https://api-sg.aliexpress.com/sync  (Singapore, global)

Auth: App Key + App Secret (HMAC-SHA256 signature per request, no OAuth)

credentials dict:
{
    "app_key":     "...",        # from AliExpress Open Platform app
    "app_secret":  "...",        # from AliExpress Open Platform app
    "tracking_id": "...",        # your affiliate tracking ID (sub_id)
}

Rate limits: ~5 QPS / 10 000 requests per day (Trial); higher on approved tiers.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional
from urllib.parse import quote

import httpx

from .base import (
    AffiliateLinkResult,
    BaseMarketplaceAdapter,
    ProductSearchResult,
    RateLimitInfo,
)

_API_URL = "https://api-sg.aliexpress.com/sync"


def _sign(params: dict, app_secret: str) -> str:
    """
    AliExpress Open Platform HMAC-SHA256 signature.
    Steps:
    1. Sort params by key (ascending).
    2. Concatenate key+value pairs (no separator).
    3. HMAC-SHA256 with app_secret, return uppercase hex.
    """
    sorted_str = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    digest = hmac.new(
        app_secret.encode("utf-8"),
        sorted_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()
    return digest


def _build_params(method: str, app_key: str, app_secret: str, extra: dict) -> dict:
    params = {
        "method": method,
        "app_key": app_key,
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
        **extra,
    }
    params["sign"] = _sign(params, app_secret)
    return params


class AliExpressAdapter(BaseMarketplaceAdapter):
    """
    AliExpress Affiliate adapter.

    Supports:
    - Product search via aliexpress.affiliate.product.query
    - Affiliate link generation via aliexpress.affiliate.link.generate
    - Hot products via aliexpress.affiliate.hotproduct.query
    """

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
        app_key = credentials["app_key"]
        app_secret = credentials["app_secret"]
        tracking_id = credentials.get("tracking_id", "")

        sort_map = {
            "relevance": "SALE_PRICE_ASC",
            "price": "SALE_PRICE_ASC",
            "price_desc": "SALE_PRICE_DESC",
            "rating": "BEST_MATCH",
            "orders": "LAST_VOLUME_DESC",
        }

        extra: dict = {
            "keywords": query,
            "page_no": str(page),
            "page_size": str(min(page_size, 50)),
            "sort": sort_map.get(sort_by, "SALE_PRICE_ASC"),
            "fields": (
                "product_id,product_title,product_main_image_url,"
                "target_sale_price,target_sale_price_currency,"
                "original_price,discount,evaluate_rate,"
                "lastest_volume,commission_rate,shop_url,"
                "product_detail_url,first_level_category_name,"
                "second_level_category_name,shop_id"
            ),
            "tracking_id": tracking_id,
        }
        if category:
            extra["category_ids"] = category
        if min_price is not None:
            extra["min_sale_price"] = str(int(min_price * 100))
        if max_price is not None:
            extra["max_sale_price"] = str(int(max_price * 100))

        params = _build_params(
            "aliexpress.affiliate.product.query", app_key, app_secret, extra
        )

        with httpx.Client(timeout=20) as client:
            resp = client.post(_API_URL, data=params)

        rate_info = RateLimitInfo()
        resp.raise_for_status()
        data = resp.json()

        resp_data = (
            data.get("aliexpress_affiliate_product_query_response", {})
            .get("resp_result", {})
        )
        if resp_data.get("resp_code") != 200:
            raise RuntimeError(
                f"AliExpress API error {resp_data.get('resp_code')}: "
                f"{resp_data.get('resp_msg')}"
            )

        items = (
            resp_data.get("result", {})
            .get("products", {})
            .get("product", [])
        )
        results = [self._parse_product(item, tracking_id) for item in items]
        return results, rate_info

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        app_key = credentials["app_key"]
        app_secret = credentials["app_secret"]
        tracking_id = credentials.get("tracking_id", "")

        extra: dict = {
            "promotion_link_type": "0",   # 0 = normal link, 2 = hot product
            "source_values": product_url,
            "tracking_id": tracking_id,
        }
        if sub_id:
            extra["sub_id"] = sub_id

        params = _build_params(
            "aliexpress.affiliate.link.generate", app_key, app_secret, extra
        )

        with httpx.Client(timeout=15) as client:
            resp = client.post(_API_URL, data=params)

        resp.raise_for_status()
        data = resp.json()

        resp_data = (
            data.get("aliexpress_affiliate_link_generate_response", {})
            .get("resp_result", {})
        )
        if resp_data.get("resp_code") != 200:
            # Fallback: construct affiliate URL manually
            return AffiliateLinkResult(
                affiliate_url=f"https://s.click.aliexpress.com/e/?aff_platform=portals-tool"
                              f"&sk={tracking_id}&aff_trace_key=&src=portals"
                              f"&terminal_id={app_key}&needsReceiver=false"
                              f"&source={quote(product_url, safe='')}",
                tracking_params={"tracking_id": tracking_id},
            )

        links = (
            resp_data.get("result", {})
            .get("promotion_links", {})
            .get("promotion_link", [])
        )
        if not links:
            raise RuntimeError("AliExpress returned no affiliate links")

        affiliate_url = links[0].get("promotion_link", product_url)
        return AffiliateLinkResult(
            affiliate_url=affiliate_url,
            tracking_params={"tracking_id": tracking_id},
        )

    def healthcheck(self, credentials: dict) -> dict:
        """Verify credentials by fetching one hot product."""
        try:
            app_key = credentials["app_key"]
            app_secret = credentials["app_secret"]
            tracking_id = credentials.get("tracking_id", "")

            params = _build_params(
                "aliexpress.affiliate.hotproduct.query",
                app_key,
                app_secret,
                {
                    "page_no": "1",
                    "page_size": "1",
                    "tracking_id": tracking_id,
                    "fields": "product_id,product_title",
                },
            )
            with httpx.Client(timeout=10) as client:
                resp = client.post(_API_URL, data=params)
            resp.raise_for_status()
            data = resp.json()
            resp_data = (
                data.get("aliexpress_affiliate_hotproduct_query_response", {})
                .get("resp_result", {})
            )
            if resp_data.get("resp_code") == 200:
                return {"status": "ok", "app_key": app_key}
            return {
                "status": "error",
                "detail": f"API code {resp_data.get('resp_code')}: {resp_data.get('resp_msg')}",
            }
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    def _parse_product(self, item: dict, tracking_id: str) -> ProductSearchResult:
        product_id = str(item.get("product_id", ""))
        detail_url = item.get("product_detail_url", "")
        if not detail_url:
            detail_url = f"https://www.aliexpress.com/item/{product_id}.html"

        # Prices come as strings like "12.99"
        sale_price = float(item.get("target_sale_price", 0) or 0)
        orig_price = float(item.get("original_price", sale_price) or sale_price)
        currency = item.get("target_sale_price_currency", "USD")

        discount_pct: Optional[float] = None
        if orig_price and orig_price > sale_price:
            discount_pct = round((1 - sale_price / orig_price) * 100, 1)

        # Commission rate comes as "5.00%"
        commission_str = item.get("commission_rate", "0%").replace("%", "")
        try:
            commission_rate = float(commission_str)
        except ValueError:
            commission_rate = 0.0

        # Rating: evaluate_rate is a string like "95.2%"
        rating_str = item.get("evaluate_rate", "").replace("%", "")
        rating: Optional[float] = None
        if rating_str:
            try:
                rating = round(float(rating_str) / 20, 1)  # convert 95% → 4.75 / 5
            except ValueError:
                pass

        category = item.get("first_level_category_name", "")
        sub_category = item.get("second_level_category_name", "")

        tags = [t for t in [category, sub_category] if t]

        return ProductSearchResult(
            external_id=product_id,
            title=item.get("product_title", ""),
            description="",
            category=category,
            price=sale_price,
            currency=currency,
            image_url=item.get("product_main_image_url", ""),
            product_url=detail_url,
            in_stock=True,  # AliExpress doesn't expose stock in affiliate API
            commission_rate=commission_rate,
            commission_type="percentage",
            original_price=orig_price if orig_price != sale_price else None,
            discount_pct=discount_pct,
            rating=rating,
            review_count=int(item.get("lastest_volume", 0) or 0),
            tags=tags,
            raw_data={
                "product_id": product_id,
                "shop_id": item.get("shop_id", ""),
                "tracking_id": tracking_id,
            },
        )
