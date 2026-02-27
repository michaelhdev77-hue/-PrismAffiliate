from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo
from .admitad import AdmitadAdapter
from .gdeslon import GdeSlonAdapter
from .amazon import AmazonAdapter

REGISTRY: dict[str, BaseMarketplaceAdapter] = {
    "admitad": AdmitadAdapter(),
    "gdeslon": GdeSlonAdapter(),
    "amazon": AmazonAdapter(),
}


def get_adapter(marketplace: str) -> BaseMarketplaceAdapter:
    adapter = REGISTRY.get(marketplace)
    if not adapter:
        raise ValueError(f"No adapter registered for marketplace: {marketplace!r}")
    return adapter
