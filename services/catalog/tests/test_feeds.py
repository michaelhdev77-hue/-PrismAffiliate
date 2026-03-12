"""Tests for /api/v1/feeds/ endpoints."""

import uuid
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProductFeed, FeedFormat, FeedStatus, MarketplaceAccount, MarketplaceType, Campaign
from shared.encryption import encrypt_json

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_account(db: AsyncSession, **overrides) -> MarketplaceAccount:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": MarketplaceType.admitad,
        "display_name": "Feed Test Account",
        "credentials_encrypted": encrypt_json({"api_key": "k"}, ENCRYPTION_KEY),
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


def _feed_payload(marketplace_account_id: str, **overrides) -> dict:
    defaults = {
        "marketplace_account_id": marketplace_account_id,
        "name": "My Feed",
        "feed_format": "xml",
        "feed_url": "https://example.com/feed.xml",
        "search_params": {"q": "laptop"},
        "schedule_cron": "0 */6 * * *",
        "category_mapping": {},
        "niche_mapping": {},
    }
    defaults.update(overrides)
    return defaults


async def _insert_feed(db: AsyncSession, marketplace_account_id: str, **overrides) -> ProductFeed:
    data = {
        "id": str(uuid.uuid4()),
        "marketplace_account_id": marketplace_account_id,
        "name": "Seeded Feed",
        "feed_format": FeedFormat.xml,
        "feed_url": "https://example.com/feed.xml",
        "search_params": {},
        "schedule_cron": "0 */6 * * *",
        "status": FeedStatus.active,
        "last_sync_products": 0,
        "category_mapping": {},
        "niche_mapping": {},
    }
    data.update(overrides)
    f = ProductFeed(**data)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feeds_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/feeds/")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_feeds_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/feeds/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_feeds(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_feed(db, acc.id, name="Feed A")
    await _insert_feed(db, acc.id, name="Feed B")

    resp = await client.get("/api/v1/feeds/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_feed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    payload = _feed_payload(acc.id)

    resp = await client.post("/api/v1/feeds/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Feed"
    assert data["feed_format"] == "xml"
    assert data["status"] == "active"
    assert data["marketplace_account_id"] == acc.id


@pytest.mark.asyncio
async def test_create_feed_with_campaign(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    camp = Campaign(
        id=str(uuid.uuid4()),
        marketplace_account_id=acc.id,
        name="Camp",
        external_campaign_id="ext-1",
    )
    db.add(camp)
    await db.commit()
    await db.refresh(camp)

    payload = _feed_payload(acc.id, campaign_id=camp.id)
    resp = await client.post("/api/v1/feeds/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    assert resp.json()["campaign_id"] == camp.id


@pytest.mark.asyncio
async def test_create_feed_json_format(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    payload = _feed_payload(acc.id, feed_format="json")
    resp = await client.post("/api/v1/feeds/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    assert resp.json()["feed_format"] == "json"


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_feed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id)

    resp = await client.get(f"/api/v1/feeds/{feed.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == feed.id


@pytest.mark.asyncio
async def test_get_feed_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/feeds/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_feed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id, name="Old")

    resp = await client.patch(
        f"/api/v1/feeds/{feed.id}",
        headers=auth_headers,
        json={"name": "New Name", "schedule_cron": "0 0 * * *"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["schedule_cron"] == "0 0 * * *"


@pytest.mark.asyncio
async def test_update_feed_status(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id)

    resp = await client.patch(
        f"/api/v1/feeds/{feed.id}",
        headers=auth_headers,
        json={"status": "paused"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_update_feed_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        f"/api/v1/feeds/{uuid.uuid4()}",
        headers=auth_headers,
        json={"name": "X"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_feed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id)

    resp = await client.delete(f"/api/v1/feeds/{feed.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/feeds/{feed.id}", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_feed_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(f"/api/v1/feeds/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_sync(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id)

    resp = await client.post(f"/api/v1/feeds/{feed.id}/sync", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sync_queued"
    assert data["feed_id"] == feed.id

    # Verify status changed to syncing
    resp2 = await client.get(f"/api/v1/feeds/{feed.id}", headers=auth_headers)
    assert resp2.json()["status"] == "syncing"


@pytest.mark.asyncio
async def test_trigger_sync_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post(f"/api/v1/feeds/{uuid.uuid4()}/sync", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trigger_sync_requires_auth(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    feed = await _insert_feed(db, acc.id)
    resp = await client.post(f"/api/v1/feeds/{feed.id}/sync")
    assert resp.status_code == 401
