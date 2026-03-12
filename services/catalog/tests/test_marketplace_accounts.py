"""Tests for /api/v1/marketplace-accounts/ endpoints."""

import uuid
import os
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketplaceAccount, MarketplaceType
from shared.encryption import encrypt_json, decrypt_json

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _account_payload(**overrides) -> dict:
    defaults = {
        "marketplace": "admitad",
        "display_name": "My Admitad Account",
        "credentials": {"api_key": "secret-key-123", "website_id": "12345"},
        "config": {"region": "RU"},
    }
    defaults.update(overrides)
    return defaults


async def _insert_account(db: AsyncSession, **overrides) -> MarketplaceAccount:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": MarketplaceType.admitad,
        "display_name": "Seeded Account",
        "credentials_encrypted": encrypt_json({"api_key": "k", "website_id": "1"}, ENCRYPTION_KEY),
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


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_accounts_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/marketplace-accounts/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_account_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/marketplace-accounts/", json=_account_payload())
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_accounts_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/marketplace-accounts/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_account(db, display_name="Acc1")
    await _insert_account(db, display_name="Acc2")

    resp = await client.get("/api/v1/marketplace-accounts/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # credentials_encrypted should NOT be in AccountOut
    for item in data:
        assert "credentials_encrypted" not in item


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_account(client: AsyncClient, auth_headers: dict):
    payload = _account_payload()
    resp = await client.post("/api/v1/marketplace-accounts/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["marketplace"] == "admitad"
    assert data["display_name"] == "My Admitad Account"
    assert data["config"] == {"region": "RU"}
    assert data["is_active"] is True
    assert data["health_status"] == "unknown"
    assert "credentials_encrypted" not in data


@pytest.mark.asyncio
async def test_create_account_credentials_encrypted(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """Verify that credentials are actually stored encrypted."""
    payload = _account_payload(credentials={"token": "my-secret-token"})
    resp = await client.post("/api/v1/marketplace-accounts/", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    account_id = resp.json()["id"]

    # Read directly from DB
    account = await db.get(MarketplaceAccount, account_id)
    assert account is not None
    assert account.credentials_encrypted != '{"token": "my-secret-token"}'
    # Verify decryption yields original data
    decrypted = decrypt_json(account.credentials_encrypted, ENCRYPTION_KEY)
    assert decrypted == {"token": "my-secret-token"}


@pytest.mark.asyncio
async def test_create_account_various_marketplaces(client: AsyncClient, auth_headers: dict):
    for mkt in ["amazon", "ebay", "aliexpress", "gdeslon"]:
        payload = _account_payload(marketplace=mkt, display_name=f"{mkt} account")
        resp = await client.post("/api/v1/marketplace-accounts/", headers=auth_headers, json=payload)
        assert resp.status_code == 201
        assert resp.json()["marketplace"] == mkt


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)
    resp = await client.get(f"/api/v1/marketplace-accounts/{acc.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == acc.id


@pytest.mark.asyncio
async def test_get_account_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/marketplace-accounts/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_account_display_name(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db, display_name="Old Name")

    resp = await client.patch(
        f"/api/v1/marketplace-accounts/{acc.id}",
        headers=auth_headers,
        json={"display_name": "New Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


@pytest.mark.asyncio
async def test_update_account_credentials(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)

    resp = await client.patch(
        f"/api/v1/marketplace-accounts/{acc.id}",
        headers=auth_headers,
        json={"credentials": {"new_key": "new_value"}},
    )
    assert resp.status_code == 200

    # Verify new credentials stored encrypted
    await db.refresh(acc)
    # Re-fetch to get updated value
    updated = await db.get(MarketplaceAccount, acc.id)
    decrypted = decrypt_json(updated.credentials_encrypted, ENCRYPTION_KEY)
    assert decrypted == {"new_key": "new_value"}


@pytest.mark.asyncio
async def test_update_account_deactivate(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db, is_active=True)

    resp = await client.patch(
        f"/api/v1/marketplace-accounts/{acc.id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_account_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        f"/api/v1/marketplace-accounts/{uuid.uuid4()}",
        headers=auth_headers,
        json={"display_name": "X"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)

    resp = await client.delete(f"/api/v1/marketplace-accounts/{acc.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/v1/marketplace-accounts/{acc.id}", headers=auth_headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_account_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(f"/api/v1/marketplace-accounts/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_healthcheck_account(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)

    mock_adapter = MagicMock()
    mock_adapter.healthcheck.return_value = {"status": "ok", "detail": "Connected"}

    with patch("app.routes.marketplace_accounts.get_adapter", return_value=mock_adapter):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/healthcheck",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # Verify health_status updated in DB
    resp2 = await client.get(f"/api/v1/marketplace-accounts/{acc.id}", headers=auth_headers)
    assert resp2.json()["health_status"] == "ok"
    assert resp2.json()["last_health_check"] is not None


@pytest.mark.asyncio
async def test_healthcheck_account_error(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)

    mock_adapter = MagicMock()
    mock_adapter.healthcheck.return_value = {"status": "error", "detail": "Auth failed"}

    with patch("app.routes.marketplace_accounts.get_adapter", return_value=mock_adapter):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/healthcheck",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_healthcheck_account_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        f"/api/v1/marketplace-accounts/{uuid.uuid4()}/healthcheck",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_healthcheck_no_adapter(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(db)

    with patch("app.routes.marketplace_accounts.get_adapter", side_effect=ValueError("No adapter")):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/healthcheck",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_healthcheck_requires_auth(client: AsyncClient, db: AsyncSession):
    acc = await _insert_account(db)
    resp = await client.post(f"/api/v1/marketplace-accounts/{acc.id}/healthcheck")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Discover Programs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discover_programs(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(
        db,
        credentials_encrypted=encrypt_json(
            {"api_key": "k", "website_id": "999"}, ENCRYPTION_KEY
        ),
    )

    mock_adapter = MagicMock()
    mock_adapter.list_programs.return_value = [
        {"id": "prog-1", "name": "Program 1"},
        {"id": "prog-2", "name": "Program 2"},
    ]

    with patch("app.routes.marketplace_accounts.get_adapter", return_value=mock_adapter):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/discover-programs",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Program 1"


@pytest.mark.asyncio
async def test_discover_programs_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        f"/api/v1/marketplace-accounts/{uuid.uuid4()}/discover-programs",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_discover_programs_no_adapter(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(
        db,
        credentials_encrypted=encrypt_json(
            {"api_key": "k", "website_id": "999"}, ENCRYPTION_KEY
        ),
    )

    with patch("app.routes.marketplace_accounts.get_adapter", side_effect=ValueError("No adapter")):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/discover-programs",
            headers=auth_headers,
        )

    assert resp.status_code == 400
    assert "No adapter" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_discover_programs_no_website_id(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(
        db,
        credentials_encrypted=encrypt_json({"api_key": "k"}, ENCRYPTION_KEY),
    )

    mock_adapter = MagicMock()

    with patch("app.routes.marketplace_accounts.get_adapter", return_value=mock_adapter):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/discover-programs",
            headers=auth_headers,
        )

    assert resp.status_code == 400
    assert "website_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_discover_programs_adapter_failure(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    acc = await _insert_account(
        db,
        credentials_encrypted=encrypt_json(
            {"api_key": "k", "website_id": "999"}, ENCRYPTION_KEY
        ),
    )

    mock_adapter = MagicMock()
    mock_adapter.list_programs.side_effect = Exception("API timeout")

    with patch("app.routes.marketplace_accounts.get_adapter", return_value=mock_adapter):
        resp = await client.post(
            f"/api/v1/marketplace-accounts/{acc.id}/discover-programs",
            headers=auth_headers,
        )

    assert resp.status_code == 502
    assert "Failed to fetch programs" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_discover_programs_requires_auth(client: AsyncClient, db: AsyncSession):
    acc = await _insert_account(db)
    resp = await client.post(f"/api/v1/marketplace-accounts/{acc.id}/discover-programs")
    assert resp.status_code == 401
