"""Tests for /internal/ routes (no auth required)."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_link_data(short_code: str = "int001", sub_id: str | None = None, channel: str | None = None) -> dict:
    return {
        "marketplace": "admitad",
        "marketplace_account_id": "acc-123",
        "affiliate_url": "https://example.com/aff?id=123",
        "short_code": short_code,
        "sub_id": sub_id,
        "channel": channel,
        "expires_at": None,
    }


# ── POST /internal/links/generate-for-content ───────────────────────

@pytest.mark.asyncio
async def test_generate_for_content_success(async_client: AsyncClient):
    product_ids = [str(uuid.uuid4()) for _ in range(2)]
    content_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    call_count = 0

    async def _mock_gen(**kwargs):
        nonlocal call_count
        call_count += 1
        return _mock_link_data(
            short_code=f"intc{call_count:03d}",
            sub_id=kwargs.get("sub_id"),
            channel=kwargs.get("channel"),
        )

    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={
                "product_ids": product_ids,
                "prism_content_id": content_id,
                "prism_project_id": project_id,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["product_id"] == product_ids[0]
    assert data[0]["marketplace"] == "admitad"
    assert "short_code" in data[0]
    assert "affiliate_url" in data[0]


@pytest.mark.asyncio
async def test_generate_for_content_with_channel(async_client: AsyncClient):
    product_id = str(uuid.uuid4())

    async def _mock_gen(**kwargs):
        return _mock_link_data(
            short_code="chann01",
            sub_id=kwargs.get("sub_id"),
            channel=kwargs.get("channel"),
        )

    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={
                "product_ids": [product_id],
                "channel": "pinterest",
                "sub_id_prefix": "pin",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_generate_for_content_partial_failure(async_client: AsyncClient):
    product_ids = [str(uuid.uuid4()) for _ in range(3)]
    call_count = 0

    async def _mock_gen(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("adapter error")
        return _mock_link_data(short_code=f"pfi{call_count:03d}")

    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={"product_ids": product_ids},
        )

    assert resp.status_code == 200
    data = resp.json()
    # 2 succeeded, 1 failed (silently skipped)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_generate_for_content_empty_products(async_client: AsyncClient):
    resp = await async_client.post(
        "/internal/links/generate-for-content",
        json={"product_ids": []},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_generate_for_content_no_auth_needed(async_client: AsyncClient):
    """Internal endpoint should work without auth headers."""
    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("noauth01"),
    ):
        resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={"product_ids": [str(uuid.uuid4())]},
        )
    assert resp.status_code == 200


# ── GET /internal/links/resolve/{short_code} ────────────────────────

@pytest.mark.asyncio
async def test_resolve_short_code(async_client: AsyncClient, auth_headers: dict):
    """Create a link via public API, then resolve via internal endpoint."""
    product_id = str(uuid.uuid4())
    short_code = "resol001"

    # Create a link first (via public API, needs auth)
    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data(short_code=short_code),
    ):
        create_resp = await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": product_id},
            headers=auth_headers,
        )
    assert create_resp.status_code == 201

    # Resolve via internal endpoint (no auth)
    resp = await async_client.get(f"/internal/links/resolve/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["affiliate_url"] == "https://example.com/aff?id=123"
    assert data["product_id"] == product_id


@pytest.mark.asyncio
async def test_resolve_short_code_not_found(async_client: AsyncClient):
    resp = await async_client.get("/internal/links/resolve/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Link not found"


@pytest.mark.asyncio
async def test_resolve_via_internal_create(async_client: AsyncClient):
    """Create via internal endpoint, then resolve."""
    product_id = str(uuid.uuid4())
    short_code = "intres01"

    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data(short_code=short_code),
    ):
        create_resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={"product_ids": [product_id]},
        )
    assert create_resp.status_code == 200
    assert len(create_resp.json()) == 1

    resp = await async_client.get(f"/internal/links/resolve/{short_code}")
    assert resp.status_code == 200
    assert resp.json()["product_id"] == product_id


# ── GET /internal/links/by-subid/{sub_id} ───────────────────────────

@pytest.mark.asyncio
async def test_get_link_by_subid(async_client: AsyncClient):
    product_id = str(uuid.uuid4())
    sub_id = f"pin_{product_id[:8]}"

    with patch(
        "app.routes.internal.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data(short_code="subid01", sub_id=sub_id, channel="pinterest"),
    ):
        create_resp = await async_client.post(
            "/internal/links/generate-for-content",
            json={
                "product_ids": [product_id],
                "channel": "pinterest",
                "sub_id_prefix": "pin",
            },
        )
    assert create_resp.status_code == 200

    resp = await async_client.get(f"/internal/links/by-subid/{sub_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == product_id
    assert data["affiliate_url"] == "https://example.com/aff?id=123"


@pytest.mark.asyncio
async def test_get_link_by_subid_not_found(async_client: AsyncClient):
    resp = await async_client.get("/internal/links/by-subid/nonexistent-subid")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Link not found"


# ── GET /internal/selection-profiles ─────────────────────────────────

@pytest.mark.asyncio
async def test_internal_list_profiles_empty(async_client: AsyncClient):
    resp = await async_client.get("/internal/selection-profiles")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_internal_list_profiles(async_client: AsyncClient, auth_headers: dict):
    """Create profiles via public API, then list via internal endpoint."""
    project_id = str(uuid.uuid4())

    # Create a profile via public API (needs auth)
    await async_client.post(
        "/api/v1/selection-profiles/",
        json={
            "prism_project_id": project_id,
            "name": "Internal Test Profile",
            "marketplaces": ["admitad"],
            "categories": ["electronics"],
            "keywords": ["phone"],
        },
        headers=auth_headers,
    )

    # List via internal endpoint (no auth)
    resp = await async_client.get("/internal/selection-profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    profile = data[0]
    assert profile["name"] == "Internal Test Profile"
    assert profile["is_active"] is True
    assert "id" in profile
    assert "prism_project_id" in profile
    assert "marketplaces" in profile


@pytest.mark.asyncio
async def test_internal_list_profiles_filter_by_project(async_client: AsyncClient, auth_headers: dict):
    proj1 = str(uuid.uuid4())
    proj2 = str(uuid.uuid4())

    # Create two profiles with different project IDs
    for proj, name in [(proj1, "Profile A"), (proj2, "Profile B")]:
        await async_client.post(
            "/api/v1/selection-profiles/",
            json={"prism_project_id": proj, "name": name},
            headers=auth_headers,
        )

    # Filter by proj1
    resp = await async_client.get(
        "/internal/selection-profiles",
        params={"prism_project_id": proj1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["prism_project_id"] == proj1
    assert data[0]["name"] == "Profile A"


@pytest.mark.asyncio
async def test_internal_list_profiles_no_auth_needed(async_client: AsyncClient):
    """Internal endpoint should work without auth headers."""
    resp = await async_client.get("/internal/selection-profiles")
    assert resp.status_code == 200
