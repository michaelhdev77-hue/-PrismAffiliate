import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx
from sqlalchemy import select

from app.models import ClickEvent


pytestmark = pytest.mark.asyncio


def _mock_resolve_response(affiliate_url: str, product_id: str, marketplace: str = "admitad"):
    """Create a mock httpx.Response for the links service resolve call."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "affiliate_url": affiliate_url,
        "product_id": product_id,
        "marketplace": marketplace,
    }
    response.raise_for_status = MagicMock()
    return response


def _mock_resolve_404():
    """Create a mock that simulates a 404 from the links service."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 404
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=response
    )
    return response


class TestClickRedirect:
    async def test_successful_redirect(self, async_client, db):
        affiliate_url = "https://example.com/product?aff=123"
        product_id = "prod-abc-123"

        mock_response = _mock_resolve_response(affiliate_url, product_id, "admitad")

        with patch("app.routes.redirect.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.get("/r/abc123", follow_redirects=False)

        assert resp.status_code == 302
        assert resp.headers["location"] == affiliate_url

    async def test_404_when_link_not_found(self, async_client):
        mock_response = _mock_resolve_404()

        with patch("app.routes.redirect.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.get("/r/unknown_code", follow_redirects=False)

        assert resp.status_code == 404

    async def test_click_event_stored(self, async_client, db):
        affiliate_url = "https://shop.example.com/item/42"
        product_id = "prod-xyz-789"
        short_code = "testcode1"

        mock_response = _mock_resolve_response(affiliate_url, product_id, "amazon")

        with patch("app.routes.redirect.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.get(
                f"/r/{short_code}",
                headers={
                    "user-agent": "TestBot/1.0",
                    "referer": "https://youtube.com/watch?v=abc",
                },
                follow_redirects=False,
            )

        assert resp.status_code == 302

        result = await db.execute(select(ClickEvent).where(ClickEvent.short_code == short_code))
        click = result.scalar_one()

        assert click.short_code == short_code
        assert click.product_id == product_id
        assert click.marketplace == "amazon"
        assert click.user_agent == "TestBot/1.0"
        assert click.referrer == "https://youtube.com/watch?v=abc"
        assert click.ip_hash == hashlib.sha256(b"127.0.0.1").hexdigest()

    async def test_click_event_stored_with_minimal_headers(self, async_client, db):
        affiliate_url = "https://shop.example.com/item/99"
        product_id = "prod-min-001"
        short_code = "mincode"

        mock_response = _mock_resolve_response(affiliate_url, product_id, "gdeslon")

        with patch("app.routes.redirect.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.get(f"/r/{short_code}", follow_redirects=False)

        assert resp.status_code == 302

        result = await db.execute(select(ClickEvent).where(ClickEvent.short_code == short_code))
        click = result.scalar_one()

        assert click.short_code == short_code
        assert click.product_id == product_id
        assert click.marketplace == "gdeslon"

    async def test_links_service_timeout(self, async_client):
        """When the links service is unreachable, return 404."""
        with patch("app.routes.redirect.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.get("/r/timeout_code", follow_redirects=False)

        assert resp.status_code == 404
