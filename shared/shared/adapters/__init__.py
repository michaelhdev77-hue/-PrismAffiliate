from .base import BaseMarketplaceAdapter, ProductSearchResult, AffiliateLinkResult, RateLimitInfo
from .admitad import AdmitadAdapter
from .gdeslon import GdeSlonAdapter
from .amazon import AmazonAdapter
from .ebay import EbayAdapter
from .cj_affiliate import CJAffiliateAdapter
from .awin import AwinAdapter
from .rakuten import RakutenAdapter

REGISTRY: dict[str, BaseMarketplaceAdapter] = {
    # Global — Tier 1
    "amazon": AmazonAdapter(),
    "ebay": EbayAdapter(),
    "rakuten": RakutenAdapter(),
    "cj_affiliate": CJAffiliateAdapter(),
    "awin": AwinAdapter(),
    # Russia / CIS
    "admitad": AdmitadAdapter(),
    "gdeslon": GdeSlonAdapter(),
}


def get_adapter(marketplace: str) -> BaseMarketplaceAdapter:
    adapter = REGISTRY.get(marketplace)
    if not adapter:
        raise ValueError(f"No adapter registered for marketplace: {marketplace!r}")
    return adapter
