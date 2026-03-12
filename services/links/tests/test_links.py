"""Tests for /api/v1/links/ routes."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


def _mock_link_data(short_code: str = "abc123") -> dict:
    return {
        "marketplace": "admitad",
        "marketplace_account_id": "acc-123",
        "affiliate_url": "https://example.com/aff?id=123",
        "short_code": short_code,
        "sub_id": None,
        "channel": None,
        "expires_at": None,
    }


# ── POST /api/v1/links/generate ─────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_link_success(async_client: AsyncClient, auth_headers: dict):
    product_id = str(uuid.uuid4())
    mock_data = _mock_link_data("gen001")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        resp = await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": product_id},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["product_id"] == product_id
    assert body["marketplace"] == "admitad"
    assert body["affiliate_url"] == mock_data["affiliate_url"]
    assert body["short_code"] == "gen001"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_generate_link_with_prism_ids(async_client: AsyncClient, auth_headers: dict):
    product_id = str(uuid.uuid4())
    content_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    mock_data = _mock_link_data("gen002")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=mock_data,
    ):
        resp = await async_client.post(
            "/api/v1/links/generate",
            json={
                "product_id": product_id,
                "prism_content_id": content_id,
                "prism_project_id": project_id,
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["prism_content_id"] == content_id
    assert body["prism_project_id"] == project_id


@pytest.mark.asyncio
async def test_generate_link_no_auth(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/links/generate",
        json={"product_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_link_missing_product_id(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.post(
        "/api/v1/links/generate",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_link_upstream_failure(async_client: AsyncClient, auth_headers: dict):
    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=Exception("catalog down"),
    ):
        resp = await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": str(uuid.uuid4())},
            headers=auth_headers,
        )

    assert resp.status_code == 502
    assert "Link generation failed" in resp.json()["detail"]


# ── POST /api/v1/links/generate-bulk ────────────────────────────────

@pytest.mark.asyncio
async def test_generate_bulk_success(async_client: AsyncClient, auth_headers: dict):
    product_ids = [str(uuid.uuid4()) for _ in range(3)]
    call_count = 0

    async def _mock_gen(**kwargs):
        nonlocal call_count
        call_count += 1
        return _mock_link_data(f"bulk{call_count:03d}")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp = await async_client.post(
            "/api/v1/links/generate-bulk",
            json={"product_ids": product_ids},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["created"] == 3
    assert body["failed"] == 0
    assert len(body["links"]) == 3


@pytest.mark.asyncio
async def test_generate_bulk_skips_existing(async_client: AsyncClient, auth_headers: dict):
    """If a product already has an active link, bulk generate should skip it."""
    product_id = str(uuid.uuid4())

    # First, create a link for this product
    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("exist01"),
    ):
        resp1 = await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": product_id},
            headers=auth_headers,
        )
    assert resp1.status_code == 201

    # Now bulk generate with the same product_id + a new one
    new_product_id = str(uuid.uuid4())

    async def _mock_gen(**kwargs):
        return _mock_link_data("exist02")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp2 = await async_client.post(
            "/api/v1/links/generate-bulk",
            json={"product_ids": [product_id, new_product_id]},
            headers=auth_headers,
        )

    assert resp2.status_code == 201
    body = resp2.json()
    # Only the new product should be created; existing one is skipped
    assert body["created"] == 1
    assert body["failed"] == 0


@pytest.mark.asyncio
async def test_generate_bulk_partial_failure(async_client: AsyncClient, auth_headers: dict):
    product_ids = [str(uuid.uuid4()) for _ in range(3)]
    call_count = 0

    async def _mock_gen(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("adapter error")
        return _mock_link_data(f"pf{call_count:03d}")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        resp = await async_client.post(
            "/api/v1/links/generate-bulk",
            json={"product_ids": product_ids},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["created"] == 2
    assert body["failed"] == 1


@pytest.mark.asyncio
async def test_generate_bulk_no_auth(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/links/generate-bulk",
        json={"product_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_bulk_with_project_id(async_client: AsyncClient, auth_headers: dict):
    product_ids = [str(uuid.uuid4())]
    project_id = str(uuid.uuid4())

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("proj01"),
    ):
        resp = await async_client.post(
            "/api/v1/links/generate-bulk",
            json={"product_ids": product_ids, "prism_project_id": project_id},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["links"][0]["prism_project_id"] == project_id


# ── GET /api/v1/links/ ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_links_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/links/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_links_returns_created(async_client: AsyncClient, auth_headers: dict):
    product_id = str(uuid.uuid4())

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("list01"),
    ):
        await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": product_id},
            headers=auth_headers,
        )

    resp = await async_client.get("/api/v1/links/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["product_id"] == product_id


@pytest.mark.asyncio
async def test_list_links_filter_by_product_id(async_client: AsyncClient, auth_headers: dict):
    pid1 = str(uuid.uuid4())
    pid2 = str(uuid.uuid4())

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=[_mock_link_data("flt01"), _mock_link_data("flt02")],
    ):
        await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": pid1},
            headers=auth_headers,
        )
        await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": pid2},
            headers=auth_headers,
        )

    resp = await async_client.get(
        "/api/v1/links/",
        params={"product_id": pid1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["product_id"] == pid1


@pytest.mark.asyncio
async def test_list_links_filter_by_prism_project_id(async_client: AsyncClient, auth_headers: dict):
    pid = str(uuid.uuid4())
    proj = str(uuid.uuid4())

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("fltpr01"),
    ):
        await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": pid, "prism_project_id": proj},
            headers=auth_headers,
        )

    resp = await async_client.get(
        "/api/v1/links/",
        params={"prism_project_id": proj},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["prism_project_id"] == proj


@pytest.mark.asyncio
async def test_list_links_pagination(async_client: AsyncClient, auth_headers: dict):
    # Create 3 links
    call_count = 0

    async def _mock_gen(**kwargs):
        nonlocal call_count
        call_count += 1
        return _mock_link_data(f"page{call_count:03d}")

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        side_effect=_mock_gen,
    ):
        for _ in range(3):
            await async_client.post(
                "/api/v1/links/generate",
                json={"product_id": str(uuid.uuid4())},
                headers=auth_headers,
            )

    # Request page 1 with per_page=2
    resp = await async_client.get(
        "/api/v1/links/",
        params={"page": 1, "per_page": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Request page 2 with per_page=2
    resp2 = await async_client.get(
        "/api/v1/links/",
        params={"page": 2, "per_page": 2},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_list_links_no_auth(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/links/")
    assert resp.status_code == 401


# ── GET /api/v1/links/{link_id} ─────────────────────────────────────

@pytest.mark.asyncio
async def test_get_link_success(async_client: AsyncClient, auth_headers: dict):
    product_id = str(uuid.uuid4())

    with patch(
        "app.routes.links.generate_link_for_product",
        new_callable=AsyncMock,
        return_value=_mock_link_data("get001"),
    ):
        create_resp = await async_client.post(
            "/api/v1/links/generate",
            json={"product_id": product_id},
            headers=auth_headers,
        )

    link_id = create_resp.json()["id"]

    resp = await async_client.get(
        f"/api/v1/links/{link_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == link_id
    assert resp.json()["product_id"] == product_id


@pytest.mark.asyncio
async def test_get_link_not_found(async_client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(
        f"/api/v1/links/{fake_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Link not found"


@pytest.mark.asyncio
async def test_get_link_no_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/api/v1/links/{uuid.uuid4()}")
    assert resp.status_code == 401
