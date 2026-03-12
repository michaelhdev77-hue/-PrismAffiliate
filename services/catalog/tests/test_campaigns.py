"""Tests for /api/v1/campaigns/ endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, MarketplaceAccount, MarketplaceType
from shared.encryption import encrypt_json
import os


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]


async def _create_account(db: AsyncSession, **overrides) -> MarketplaceAccount:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": MarketplaceType.admitad,
        "display_name": "Test Account",
        "credentials_encrypted": encrypt_json({"api_key": "xxx"}, ENCRYPTION_KEY),
        "config": {},
        "is_active": True,
        "health_status": "unknown",
    }
    defaults.update(overrides)
    a = MarketplaceAccount(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


def _campaign_payload(marketplace_account_id: str, **overrides) -> dict:
    defaults = {
        "marketplace_account_id": marketplace_account_id,
        "name": "My Campaign",
        "external_campaign_id": "ext-123",
        "marketplace_label": "admitad",
        "config": {"key": "value"},
    }
    defaults.update(overrides)
    return defaults


async def _insert_campaign(db: AsyncSession, marketplace_account_id: str, **overrides) -> Campaign:
    data = {
        "id": str(uuid.uuid4()),
        "marketplace_account_id": marketplace_account_id,
        "name": "Seeded Campaign",
        "external_campaign_id": str(uuid.uuid4()),
        "marketplace_label": "admitad",
        "config": {},
        "is_active": True,
    }
    data.update(overrides)
    c = Campaign(**data)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_campaigns_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/campaigns/")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_campaigns_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/campaigns/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_campaigns(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_campaign(db, acc.id, name="Camp A")
    await _insert_campaign(db, acc.id, name="Camp B", external_campaign_id="ext-b")

    resp = await client.get("/api/v1/campaigns/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_campaigns_filter_by_account(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc1 = await _create_account(db)
    acc2 = await _create_account(db)
    await _insert_campaign(db, acc1.id, name="Acc1 Camp")
    await _insert_campaign(db, acc2.id, name="Acc2 Camp", external_campaign_id="ext-acc2")

    resp = await client.get(
        "/api/v1/campaigns/", headers=auth_headers, params={"marketplace_account_id": acc1.id}
    )
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Acc1 Camp"


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    payload = _campaign_payload(acc.id)

    resp = await client.post("/api/v1/campaigns/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["marketplace_account_id"] == acc.id
    assert data["external_campaign_id"] == "ext-123"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_campaign_account_not_found(client: AsyncClient, auth_headers: dict):
    payload = _campaign_payload(str(uuid.uuid4()))
    resp = await client.post("/api/v1/campaigns/", headers=auth_headers, json=payload)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    camp = await _insert_campaign(db, acc.id)

    resp = await client.get(f"/api/v1/campaigns/{camp.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == camp.id


@pytest.mark.asyncio
async def test_get_campaign_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/campaigns/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_campaign(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    camp = await _insert_campaign(db, acc.id, name="Old Name")

    resp = await client.patch(
        f"/api/v1/campaigns/{camp.id}",
        headers=auth_headers,
        json={"name": "New Name", "is_active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_campaign_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        f"/api/v1/campaigns/{uuid.uuid4()}",
        headers=auth_headers,
        json={"name": "X"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_campaign(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    camp = await _insert_campaign(db, acc.id)

    resp = await client.delete(f"/api/v1/campaigns/{camp.id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify gone
    resp2 = await client.get(f"/api/v1/campaigns/{camp.id}", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_campaign_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(f"/api/v1/campaigns/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
