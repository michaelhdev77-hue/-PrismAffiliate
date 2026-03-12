"""Bridge: push top affiliate products to PRISM as Pinterest pin drafts."""
import asyncio
import logging
import httpx
from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

CATALOG_URL = settings.catalog_service_url  # http://catalog:8011
LINKS_URL = settings.links_service_url      # http://links:8012
PRISM_CONTENT_URL = settings.prism_content_url  # http://content:8007 via prism_shared network

MKT_LABELS = {
    'amazon': 'Amazon', 'ebay': 'eBay', 'rakuten': 'Rakuten',
    'cj_affiliate': 'CJ Affiliate', 'awin': 'Awin',
    'admitad': 'Admitad', 'gdeslon': 'GdeSlon',
    'aliexpress': 'AliExpress', 'yandex_market': 'Яндекс.Маркет',
}

BG_STYLES = ['oat', 'indigo', 'cherry', 'sage', 'butter']


@celery_app.task(name="affiliate.push_products_to_prism", bind=True, max_retries=2)
def push_products_to_prism(self, prism_project_id: str = None, max_products: int = 10):
    """Select top products and push to PRISM as Pinterest pin drafts."""
    try:
        asyncio.run(_push_products(prism_project_id, max_products))
    except Exception as exc:
        logger.exception("Bridge task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _push_products(prism_project_id: str = None, max_products: int = 10):
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Get selection profiles from links service (internal, no JWT)
        resp = await client.get(f"{LINKS_URL}/internal/selection-profiles")
        profiles = resp.json() if resp.status_code == 200 else []

        if prism_project_id:
            profiles = [p for p in profiles if p.get("prism_project_id") == prism_project_id]

        if not profiles:
            # If no profiles, use a default: get top products across all marketplaces
            await _push_default(client, prism_project_id, max_products)
            return

        for profile in profiles:
            if not profile.get("is_active", True):
                continue

            pid = profile["prism_project_id"]

            # 2. Fetch top products from catalog internal API
            params = {"limit": str(min(profile.get("max_products", max_products), max_products))}
            if profile.get("categories"):
                params["category"] = ",".join(profile["categories"])
            if profile.get("marketplaces"):
                params["marketplace"] = ",".join(profile["marketplaces"])
            if profile.get("min_commission_rate"):
                params["min_commission"] = str(profile["min_commission_rate"])

            resp = await client.get(
                f"{CATALOG_URL}/internal/products/for-project/{pid}",
                params=params,
            )
            if resp.status_code != 200:
                logger.warning("Failed to fetch products for project %s: %s", pid, resp.text)
                continue

            products = resp.json()
            if not products:
                logger.info("No products found for project %s", pid)
                continue

            # 3. Check which products already have posts in PRISM (avoid duplicates)
            existing_urls = set()
            try:
                resp2 = await client.get(
                    f"{PRISM_CONTENT_URL}/internal/posts",
                    params={"project_id": pid, "platform": "pinterest", "limit": "200"},
                )
                if resp2.status_code == 200:
                    for post in resp2.json():
                        if post.get("product_image_url"):
                            existing_urls.add(post["product_image_url"])
            except Exception:
                pass

            products = [p for p in products if p.get("image_url") not in existing_urls]
            if not products:
                logger.info("All products already have posts for project %s", pid)
                continue

            # 4. Generate direct affiliate links with subid
            product_ids = [p["id"] for p in products]
            link_resp = await client.post(
                f"{LINKS_URL}/internal/links/generate-for-content",
                json={
                    "product_ids": product_ids,
                    "prism_project_id": pid,
                    "channel": "pinterest",
                    "sub_id_prefix": f"pin_{pid[:8]}",
                },
            )

            links_map = {}
            if link_resp.status_code == 200:
                for link in link_resp.json():
                    links_map[link["product_id"]] = link["affiliate_url"]

            # 5. Create posts in PRISM content-service
            posts_created = 0
            for i, product in enumerate(products):
                affiliate_url = links_map.get(product["id"], product.get("product_url", ""))
                if not affiliate_url:
                    continue

                store = MKT_LABELS.get(product.get("marketplace", ""), product.get("marketplace", ""))
                bg = BG_STYLES[i % len(BG_STYLES)]

                post_data = {
                    "project_id": pid,
                    "platform": "pinterest",
                    "title": product["title"][:100],
                    "product_image_url": product.get("image_url", ""),
                    "link_url": affiliate_url,
                    "store_name": store,
                    "bg_style": bg,
                }

                try:
                    create_resp = await client.post(
                        f"{PRISM_CONTENT_URL}/internal/posts",
                        json=post_data,
                    )
                    if create_resp.status_code in (200, 201):
                        post_id = create_resp.json().get("id")
                        if post_id:
                            # 6. Trigger image generation
                            await client.post(
                                f"{PRISM_CONTENT_URL}/internal/posts/{post_id}/generate-image"
                            )
                            posts_created += 1
                except Exception as e:
                    logger.warning("Failed to create post for product %s: %s", product["id"], e)

            logger.info("Created %d posts for project %s", posts_created, pid)


async def _push_default(client: httpx.AsyncClient, prism_project_id: str, max_products: int):
    """Fallback: push top products without a selection profile."""
    params = {
        "limit": str(max_products),
        "has_image": "true",
    }
    resp = await client.get(
        f"{CATALOG_URL}/internal/products/for-project/{prism_project_id or 'default'}",
        params=params,
    )
    if resp.status_code != 200:
        logger.warning("Failed to fetch default products: %s", resp.text)
        return

    products = resp.json()
    if not products:
        return

    product_ids = [p["id"] for p in products]
    link_resp = await client.post(
        f"{LINKS_URL}/internal/links/generate-for-content",
        json={
            "product_ids": product_ids,
            "prism_project_id": prism_project_id or "default",
            "channel": "pinterest",
            "sub_id_prefix": "pin_default",
        },
    )

    links_map = {}
    if link_resp.status_code == 200:
        for link in link_resp.json():
            links_map[link["product_id"]] = link["affiliate_url"]

    for i, product in enumerate(products):
        affiliate_url = links_map.get(product["id"], "")
        if not affiliate_url:
            continue

        store = MKT_LABELS.get(product.get("marketplace", ""), product.get("marketplace", ""))

        post_data = {
            "project_id": prism_project_id or "default",
            "platform": "pinterest",
            "title": product["title"][:100],
            "product_image_url": product.get("image_url", ""),
            "link_url": affiliate_url,
            "store_name": store,
            "bg_style": BG_STYLES[i % len(BG_STYLES)],
        }

        try:
            create_resp = await client.post(
                f"{PRISM_CONTENT_URL}/internal/posts",
                json=post_data,
            )
            if create_resp.status_code in (200, 201):
                post_id = create_resp.json().get("id")
                if post_id:
                    await client.post(
                        f"{PRISM_CONTENT_URL}/internal/posts/{post_id}/generate-image"
                    )
        except Exception as e:
            logger.warning("Failed to create default post: %s", e)
