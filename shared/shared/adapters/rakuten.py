"""Rakuten Advertising adapter — Product Search API + Deep Links."""
import time
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import quote_plus

import httpx

from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo


class RakutenAdapter(BaseMarketplaceAdapter):
    """Rakuten Advertising (formerly LinkShare) adapter.

    Credentials:
        username: str       — Rakuten Advertising account username
        password: str       — account password
        sid: str            — Publisher Site ID (scope)
        publisher_id: str   — 11-char encrypted publisher tracking ID for deep links
        access_token: str   — cached, auto-refreshed (60 min TTL)
        refresh_token: str  — for token renewal
        token_expires_at: str — epoch timestamp
    """

    TOKEN_URL = "https://api.rakutenadvertising.com/token"
    SEARCH_URL = "https://api.rakutenadvertising.com/productsearch/1.0"
    DEEP_LINK_BASE = "https://click.linksynergy.com/deeplink"

    def _get_token(self, credentials: dict) -> str:
        now = time.time()
        expires_at = float(credentials.get("token_expires_at", 0))
        if credentials.get("access_token") and now < expires_at - 60:
            return credentials["access_token"]
        return self._refresh_token(credentials)

    def _refresh_token(self, credentials: dict) -> str:
        # Try refresh_token first, fall back to password grant
        refresh_token = credentials.get("refresh_token")
        if refresh_token:
            try:
                return self._grant_refresh(credentials, refresh_token)
            except Exception:
                pass
        return self._grant_password(credentials)

    def _grant_password(self, credentials: dict) -> str:
        resp = httpx.post(
            self.TOKEN_URL,
            data={
                "grant_type": "password",
                "username": credentials["username"],
                "password": credentials["password"],
                "scope": credentials["sid"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return self._store_token(credentials, resp.json())

    def _grant_refresh(self, credentials: dict, refresh_token: str) -> str:
        resp = httpx.post(
            self.TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return self._store_token(credentials, resp.json())

    def _store_token(self, credentials: dict, data: dict) -> str:
        token = data["access_token"]
        credentials["access_token"] = token
        credentials["token_expires_at"] = str(time.time() + data.get("expires_in", 3600))
        if "refresh_token" in data:
            credentials["refresh_token"] = data["refresh_token"]
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

        sort_map = {"price": "retailprice", "rating": "retailprice", "newest": "createdon"}

        params: dict = {
            "keyword": query,
            "max": min(page_size, 50),
            "pagenumber": page,
            "sort": sort_map.get(sort_by, "retailprice"),
            "sorttype": "desc",
        }
        if category:
            params["cat"] = category

        resp = httpx.get(
            self.SEARCH_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/xml",
            },
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

        results = []
        for item in root.findall(".//item"):
            def t(tag: str) -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            def price_val(tag: str) -> Optional[float]:
                el = item.find(tag)
                if el is not None and el.text:
                    try:
                        return float(el.text.strip())
                    except ValueError:
                        pass
                return None

            price = price_val("saleprice") or price_val("price") or 0.0
            orig_price = price_val("price")
            currency_el = item.find("price")
            currency = currency_el.get("currency", "USD") if currency_el is not None else "USD"

            # linkurl already has affiliate tracking embedded
            affiliate_url = t("linkurl")

            cat_primary = t("./category/primary")
            cat_secondary = t("./category/secondary")
            category = f"{cat_primary} > {cat_secondary}" if cat_secondary else cat_primary

            results.append(ProductSearchResult(
                external_id=t("sku") or t("mid"),
                title=t("productname"),
                description=t("description"),
                category=category,
                price=price,
                currency=currency,
                image_url=t("imageurl"),
                product_url=affiliate_url,
                in_stock=True,
                commission_rate=0.0,
                commission_type="percentage",
                brand=t("merchantname"),
                original_price=orig_price if orig_price != price else None,
                raw_data={el.tag: el.text for el in item},
            ))
        return results

    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        """Generate a Rakuten deep link."""
        publisher_id = credentials.get("publisher_id", "")
        encoded = quote_plus(product_url)
        url = f"{self.DEEP_LINK_BASE}?id={publisher_id}&murl={encoded}"
        if sub_id:
            url += f"&u1={sub_id}"
        return AffiliateLinkResult(
            affiliate_url=url,
            tracking_params={"publisher_id": publisher_id, "sub_id": sub_id},
        )

    def healthcheck(self, credentials: dict) -> dict:
        try:
            self._refresh_token(credentials)
            return {"status": "ok", "sid": credentials.get("sid")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
