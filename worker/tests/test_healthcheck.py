"""Tests for healthcheck task — _healthcheck_all() async function."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.tasks.healthcheck import _healthcheck_all
from app.config import settings


def _make_response(status_code: int = 200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or []
    resp.text = ""
    return resp


ACCOUNTS = [
    {"id": "acc-1", "is_active": True, "marketplace": "gdeslon"},
    {"id": "acc-2", "is_active": True, "marketplace": "admitad"},
    {"id": "acc-3", "is_active": False, "marketplace": "amazon"},
]


@pytest.mark.asyncio
async def test_healthcheck_calls_active_accounts():
    """Should POST healthcheck for each active account."""
    healthcheck_calls = []

    async def mock_get(url, **kwargs):
        return _make_response(200, ACCOUNTS)

    async def mock_post(url, **kwargs):
        healthcheck_calls.append(url)
        return _make_response(200, {"status": "ok"})

    with patch("app.tasks.healthcheck.httpx.AsyncClient") as MockClientClass:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.post = AsyncMock(side_effect=mock_post)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _healthcheck_all()

    # Only active accounts (acc-1, acc-2) should get healthcheck calls
    assert len(healthcheck_calls) == 2
    assert any("acc-1" in url for url in healthcheck_calls)
    assert any("acc-2" in url for url in healthcheck_calls)
    # Inactive acc-3 should NOT be called
    assert not any("acc-3" in url for url in healthcheck_calls)


@pytest.mark.asyncio
async def test_healthcheck_skips_when_list_fails():
    """If listing accounts fails, no healthcheck calls should happen."""
    async def mock_get(url, **kwargs):
        return _make_response(500)

    with patch("app.tasks.healthcheck.httpx.AsyncClient") as MockClientClass:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.post = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _healthcheck_all()

    # post should never be called
    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_healthcheck_continues_on_individual_failure():
    """If one account healthcheck fails, others should still be checked."""
    call_count = {"n": 0}

    async def mock_get(url, **kwargs):
        return _make_response(200, ACCOUNTS)

    async def mock_post(url, **kwargs):
        call_count["n"] += 1
        if "acc-1" in url:
            raise httpx.ConnectError("Connection refused")
        return _make_response(200, {"status": "ok"})

    with patch("app.tasks.healthcheck.httpx.AsyncClient") as MockClientClass:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.post = AsyncMock(side_effect=mock_post)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        # Should not raise despite individual failure
        await _healthcheck_all()

    # Both active accounts should have been attempted
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_healthcheck_empty_accounts():
    """Empty accounts list should result in no healthcheck calls."""
    async def mock_get(url, **kwargs):
        return _make_response(200, [])

    with patch("app.tasks.healthcheck.httpx.AsyncClient") as MockClientClass:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.post = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _healthcheck_all()

    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_healthcheck_correct_urls():
    """Verify the exact URLs used for listing and healthchecking."""
    captured_get_urls = []
    captured_post_urls = []

    async def mock_get(url, **kwargs):
        captured_get_urls.append(url)
        return _make_response(200, [{"id": "acc-1", "is_active": True}])

    async def mock_post(url, **kwargs):
        captured_post_urls.append(url)
        return _make_response(200)

    with patch("app.tasks.healthcheck.httpx.AsyncClient") as MockClientClass:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.post = AsyncMock(side_effect=mock_post)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        MockClientClass.return_value = mock_ctx

        await _healthcheck_all()

    assert len(captured_get_urls) == 1
    assert "/api/v1/marketplace-accounts/" in captured_get_urls[0]
    assert len(captured_post_urls) == 1
    assert "/api/v1/marketplace-accounts/acc-1/healthcheck" in captured_post_urls[0]
