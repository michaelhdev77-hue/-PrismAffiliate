"""
End-to-end test against running Docker services.
Uses httpx to call real APIs.

Skips automatically if services are not running.
"""
import os
import uuid

import pytest
import httpx

CATALOG_URL = os.getenv("E2E_CATALOG_URL", "http://localhost:8011")
LINKS_URL = os.getenv("E2E_LINKS_URL", "http://localhost:8012")
TRACKER_URL = os.getenv("E2E_TRACKER_URL", "http://localhost:8013")
ANALYTICS_URL = os.getenv("E2E_ANALYTICS_URL", "http://localhost:8014")

# A dev JWT token for testing (same as frontend DEV_TOKEN)
DEV_TOKEN = os.getenv(
    "E2E_JWT_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20ifQ.C6IfQR8RJT1TLFB1S72r188jOCUqbyNNkjX6JrhmAfM",
)


def _headers():
    return {
        "Authorization": f"Bearer {DEV_TOKEN}",
        "Content-Type": "application/json",
    }


def _services_available() -> bool:
    """Check if the services are running."""
    try:
        resp = httpx.get(f"{CATALOG_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _services_available(),
    reason="Docker services not running — skipping E2E tests",
)


@pytest.fixture(scope="module")
def client():
    with httpx.Client(timeout=30, headers=_headers()) as c:
        yield c


@pytest.fixture(scope="module")
def async_client():
    return httpx.AsyncClient(timeout=30, headers=_headers())


class TestFullFlow:
    """Full end-to-end flow: account -> campaign -> feed -> products -> link."""

    account_id: str = ""
    campaign_id: str = ""
    feed_id: str = ""
    product_id: str = ""
    link_id: str = ""

    def test_01_create_account(self, client: httpx.Client):
        """Create a marketplace account."""
        resp = client.post(
            f"{CATALOG_URL}/api/v1/marketplace-accounts/",
            json={
                "marketplace": "gdeslon",
                "display_name": f"E2E Test Account {uuid.uuid4().hex[:8]}",
                "credentials": {"api_key": "test-key-e2e", "affiliate_id": "test-aff"},
            },
        )
        assert resp.status_code in (200, 201), f"Create account failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        TestFullFlow.account_id = data["id"]

    def test_02_create_campaign(self, client: httpx.Client):
        """Create a campaign linked to the account."""
        assert TestFullFlow.account_id, "Account must be created first"
        resp = client.post(
            f"{CATALOG_URL}/api/v1/campaigns/",
            json={
                "marketplace_account_id": TestFullFlow.account_id,
                "name": f"E2E Campaign {uuid.uuid4().hex[:8]}",
                "external_campaign_id": "ext-camp-e2e",
            },
        )
        assert resp.status_code in (200, 201), f"Create campaign failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        TestFullFlow.campaign_id = data["id"]

    def test_03_create_feed(self, client: httpx.Client):
        """Create a product feed."""
        assert TestFullFlow.account_id, "Account must be created first"
        resp = client.post(
            f"{CATALOG_URL}/api/v1/feeds/",
            json={
                "marketplace_account_id": TestFullFlow.account_id,
                "campaign_id": TestFullFlow.campaign_id,
                "name": f"E2E Feed {uuid.uuid4().hex[:8]}",
                "feed_format": "yml",
                "feed_url": "https://example.com/test-feed.xml",
                "schedule_cron": "0 */6 * * *",
            },
        )
        assert resp.status_code in (200, 201), f"Create feed failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        TestFullFlow.feed_id = data["id"]

    def test_04_search_products(self, client: httpx.Client):
        """Search for products in catalog."""
        resp = client.get(
            f"{CATALOG_URL}/api/v1/products/",
            params={"page": "1", "limit": "10"},
        )
        assert resp.status_code == 200, f"Search products failed: {resp.text}"
        data = resp.json()
        assert "items" in data
        # If there are products, grab one for link generation
        if data["items"]:
            TestFullFlow.product_id = data["items"][0]["id"]

    def test_05_generate_link(self, client: httpx.Client):
        """Generate an affiliate link for a product."""
        if not TestFullFlow.product_id:
            pytest.skip("No products available to generate link for")

        resp = client.post(
            f"{LINKS_URL}/api/v1/links/generate",
            json={"product_id": TestFullFlow.product_id},
        )
        assert resp.status_code in (200, 201), f"Generate link failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert "affiliate_url" in data
        assert data["affiliate_url"].startswith("http")
        TestFullFlow.link_id = data["id"]

    def test_06_verify_link_exists(self, client: httpx.Client):
        """Verify the generated link appears in the links list."""
        if not TestFullFlow.link_id:
            pytest.skip("No link was generated")

        resp = client.get(f"{LINKS_URL}/api/v1/links/")
        assert resp.status_code == 200, f"List links failed: {resp.text}"
        data = resp.json()
        link_ids = [link["id"] for link in data]
        assert TestFullFlow.link_id in link_ids

    def test_07_analytics_overview(self, client: httpx.Client):
        """Verify analytics endpoint is reachable."""
        resp = client.get(
            f"{ANALYTICS_URL}/api/v1/analytics/overview",
            params={"period": "30"},
        )
        assert resp.status_code == 200, f"Analytics overview failed: {resp.text}"
        data = resp.json()
        assert "total_clicks" in data

    def test_08_cleanup_feed(self, client: httpx.Client):
        """Clean up: delete feed."""
        if not TestFullFlow.feed_id:
            pytest.skip("No feed to clean up")
        resp = client.delete(f"{CATALOG_URL}/api/v1/feeds/{TestFullFlow.feed_id}")
        assert resp.status_code in (200, 204, 404)

    def test_09_cleanup_campaign(self, client: httpx.Client):
        """Clean up: delete campaign."""
        if not TestFullFlow.campaign_id:
            pytest.skip("No campaign to clean up")
        resp = client.delete(f"{CATALOG_URL}/api/v1/campaigns/{TestFullFlow.campaign_id}")
        assert resp.status_code in (200, 204, 404)

    def test_10_cleanup_account(self, client: httpx.Client):
        """Clean up: delete account."""
        if not TestFullFlow.account_id:
            pytest.skip("No account to clean up")
        resp = client.delete(f"{CATALOG_URL}/api/v1/marketplace-accounts/{TestFullFlow.account_id}")
        assert resp.status_code in (200, 204, 404)


@pytest.mark.asyncio
async def test_tracker_redirect():
    """Test that tracker service redirects short links."""
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        # Try a non-existent short code — should return 404 or 302
        resp = await client.get(f"{TRACKER_URL}/r/nonexistent-code")
        # 404 is expected for a non-existent code
        assert resp.status_code in (302, 404), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_catalog_health():
    """Verify catalog service health endpoint."""
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(f"{CATALOG_URL}/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_links_health():
    """Verify links service health endpoint."""
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(f"{LINKS_URL}/health")
        assert resp.status_code == 200
