from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class ProductSearchResult:
    external_id: str
    title: str
    description: str
    category: str
    price: float
    currency: str
    image_url: str
    product_url: str
    in_stock: bool
    commission_rate: float
    commission_type: str  # "percentage" | "fixed" | "cpa"
    tags: list[str] = field(default_factory=list)
    brand: Optional[str] = None
    original_price: Optional[float] = None
    discount_pct: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    raw_data: dict = field(default_factory=dict)


@dataclass
class AffiliateLinkResult:
    affiliate_url: str
    tracking_params: dict = field(default_factory=dict)
    expires_at: Optional[str] = None  # ISO-8601


@dataclass
class RateLimitInfo:
    requests_remaining: int = -1
    requests_limit: int = -1
    reset_at: Optional[str] = None


class BaseMarketplaceAdapter(ABC):
    """
    Abstract base for all marketplace / affiliate-network adapters.
    Instantiated once and reused (stateless — credentials passed per call).
    """

    @abstractmethod
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
        """Search marketplace for products. Returns (results, rate_limit_info)."""
        ...

    @abstractmethod
    def generate_affiliate_link(
        self,
        product_url: str,
        credentials: dict,
        sub_id: Optional[str] = None,
    ) -> AffiliateLinkResult:
        """Convert a product URL into an affiliate-tracked URL."""
        ...

    def fetch_program_feeds(self, credentials: dict, website_id: str) -> list[dict]:
        """Fetch available product feeds. Override in adapters that support this."""
        return []

    def fetch_feed(self, feed_url: str, credentials: dict) -> bytes:
        """Download a product feed file. Default implementation: plain HTTP GET."""
        resp = httpx.get(feed_url, timeout=300, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    def healthcheck(self, credentials: dict) -> dict:
        """Verify that credentials are valid. Returns {"status": "ok"|"error", ...}."""
        return {"status": "ok"}

    @staticmethod
    def _make_cache_key(*parts: str) -> str:
        return hashlib.md5(":".join(parts).encode()).hexdigest()
