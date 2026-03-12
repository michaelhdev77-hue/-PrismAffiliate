"""Tests for /api/v1/selection-profiles/ routes."""
import uuid

import pytest
from httpx import AsyncClient


def _profile_payload(prism_project_id: str | None = None, name: str = "Test Profile") -> dict:
    return {
        "prism_project_id": prism_project_id or str(uuid.uuid4()),
        "name": name,
        "marketplaces": ["admitad", "aliexpress"],
        "categories": ["electronics"],
        "keywords": ["smartphone", "gadget"],
        "min_commission_rate": 5.0,
        "min_rating": 4.0,
        "min_review_count": 10,
        "price_range_min": 10.0,
        "price_range_max": 500.0,
        "sort_by": "commission",
        "max_products": 10,
    }


# ── POST /api/v1/selection-profiles/ ────────────────────────────────

@pytest.mark.asyncio
async def test_create_profile(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == payload["name"]
    assert body["prism_project_id"] == payload["prism_project_id"]
    assert body["marketplaces"] == ["admitad", "aliexpress"]
    assert body["min_commission_rate"] == 5.0
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_profile_defaults(async_client: AsyncClient, auth_headers: dict):
    """Create with minimal fields, check defaults."""
    resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json={"prism_project_id": str(uuid.uuid4()), "name": "Minimal"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["marketplaces"] == []
    assert body["categories"] == []
    assert body["keywords"] == []
    assert body["min_commission_rate"] == 0.0
    assert body["sort_by"] == "commission"
    assert body["max_products"] == 5


@pytest.mark.asyncio
async def test_create_profile_no_auth(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=_profile_payload(),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_profile_missing_required(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json={"name": "No project ID"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── GET /api/v1/selection-profiles/ ──────────────────────────────────

@pytest.mark.asyncio
async def test_list_profiles_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/selection-profiles/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_profiles_returns_created(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )

    resp = await async_client.get("/api/v1/selection-profiles/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == payload["name"]


@pytest.mark.asyncio
async def test_list_profiles_no_auth(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/selection-profiles/")
    assert resp.status_code == 401


# ── GET /api/v1/selection-profiles/{id} ──────────────────────────────

@pytest.mark.asyncio
async def test_get_profile(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    create_resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )
    profile_id = create_resp.json()["id"]

    resp = await async_client.get(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == profile_id
    assert resp.json()["name"] == payload["name"]


@pytest.mark.asyncio
async def test_get_profile_not_found(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get(
        f"/api/v1/selection-profiles/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Profile not found"


@pytest.mark.asyncio
async def test_get_profile_no_auth(async_client: AsyncClient):
    resp = await async_client.get(f"/api/v1/selection-profiles/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── PATCH /api/v1/selection-profiles/{id} ────────────────────────────

@pytest.mark.asyncio
async def test_update_profile(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    create_resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )
    profile_id = create_resp.json()["id"]

    updated_payload = _profile_payload(
        prism_project_id=payload["prism_project_id"],
        name="Updated Profile",
    )
    updated_payload["max_products"] = 20
    updated_payload["min_rating"] = 4.5

    resp = await async_client.patch(
        f"/api/v1/selection-profiles/{profile_id}",
        json=updated_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Updated Profile"
    assert body["max_products"] == 20
    assert body["min_rating"] == 4.5


@pytest.mark.asyncio
async def test_update_profile_not_found(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    resp = await async_client.patch(
        f"/api/v1/selection-profiles/{uuid.uuid4()}",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_profile_no_auth(async_client: AsyncClient):
    resp = await async_client.patch(
        f"/api/v1/selection-profiles/{uuid.uuid4()}",
        json=_profile_payload(),
    )
    assert resp.status_code == 401


# ── DELETE /api/v1/selection-profiles/{id} ───────────────────────────

@pytest.mark.asyncio
async def test_delete_profile(async_client: AsyncClient, auth_headers: dict):
    payload = _profile_payload()
    create_resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )
    profile_id = create_resp.json()["id"]

    resp = await async_client.delete(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await async_client.get(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_not_found(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.delete(
        f"/api/v1/selection-profiles/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_no_auth(async_client: AsyncClient):
    resp = await async_client.delete(f"/api/v1/selection-profiles/{uuid.uuid4()}")
    assert resp.status_code == 401


# ── Full CRUD flow ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_crud_flow(async_client: AsyncClient, auth_headers: dict):
    """Create -> List -> Get -> Update -> Delete complete cycle."""
    project_id = str(uuid.uuid4())
    payload = _profile_payload(prism_project_id=project_id, name="CRUD Test")

    # Create
    create_resp = await async_client.post(
        "/api/v1/selection-profiles/",
        json=payload,
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    # List
    list_resp = await async_client.get(
        "/api/v1/selection-profiles/",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    assert any(p["id"] == profile_id for p in list_resp.json())

    # Get
    get_resp = await async_client.get(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "CRUD Test"

    # Update
    update_payload = _profile_payload(prism_project_id=project_id, name="Updated CRUD")
    update_resp = await async_client.patch(
        f"/api/v1/selection-profiles/{profile_id}",
        json=update_payload,
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated CRUD"

    # Delete
    delete_resp = await async_client.delete(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 204

    # Verify deleted
    final_get = await async_client.get(
        f"/api/v1/selection-profiles/{profile_id}",
        headers=auth_headers,
    )
    assert final_get.status_code == 404
