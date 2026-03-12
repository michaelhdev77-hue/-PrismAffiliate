"""Tests for /internal/ endpoints (no auth required)."""

import uuid
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, MarketplaceAccount, Campaign, MarketplaceType
from shared.encryption import encrypt_json

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_account(db: AsyncSession, **overrides) -> MarketplaceAccount:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": MarketplaceType.admitad,
        "display_name": "Internal Test Account",
        "credentials_encrypted": encrypt_json({"api_key": "k"}, ENCRYPTION_KEY),
        "config": {},
        "is_active": True,
        "health_status": "ok",
    }
    defaults.update(overrides)
    a = MarketplaceAccount(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _insert_product(db: AsyncSession, **overrides) -> Product:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": "admitad",
        "marketplace_account_id": overrides.pop("marketplace_account_id", str(uuid.uuid4())),
        "external_id": str(uuid.uuid4()),
        "title": "Internal Product",
        "description": "desc",
        "category": "Electronics",
        "brand": "Brand",
        "price": 100.0,
        "currency": "RUB",
        "original_price": 120.0,
        "discount_pct": 16.7,
        "image_url": "https://img.com/1.jpg",
        "product_url": "https://example.com/p",
        "rating": 4.0,
        "review_count": 50,
        "in_stock": True,
        "commission_rate": 5.0,
        "commission_type": "percentage",
        "tags": ["tag1"],
        "niche": "tech",
        "campaign_id": None,
        "feed_id": None,
        "is_active": True,
    }
    defaults.update(overrides)
    p = Product(**defaults)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# /internal/products/for-project/{project_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_for_project_no_auth_required(client: AsyncClient):
    """Internal endpoints should NOT require auth."""
    resp = await client.get("/internal/products/for-project/some-project-id")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_for_project_returns_sorted_by_commission_rating(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="High", commission_rate=10.0, rating=5.0, external_id="h1")
    await _insert_product(db, marketplace_account_id=acc.id, title="Medium", commission_rate=5.0, rating=4.0, external_id="m1")
    await _insert_product(db, marketplace_account_id=acc.id, title="Low", commission_rate=1.0, rating=2.0, external_id="l1")

    resp = await client.get("/internal/products/for-project/proj-1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Sorted by commission desc, then rating desc
    assert data[0]["title"] == "High"
    assert data[1]["title"] == "Medium"
    assert data[2]["title"] == "Low"


@pytest.mark.asyncio
async def test_for_project_respects_limit(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    for i in range(10):
        await _insert_product(db, marketplace_account_id=acc.id, title=f"P{i}", external_id=f"lim-{i}")

    resp = await client.get("/internal/products/for-project/proj-1", params={"limit": 3})
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_for_project_filter_has_image(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="WithImg", image_url="https://img.com/a.jpg", external_id="fi1")
    await _insert_product(db, marketplace_account_id=acc.id, title="NoImg", image_url="", external_id="fi2")

    resp = await client.get("/internal/products/for-project/proj-1", params={"has_image": True})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "WithImg"


@pytest.mark.asyncio
async def test_for_project_filter_marketplace(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="Admitad", marketplace="admitad", external_id="fm1")
    await _insert_product(db, marketplace_account_id=acc.id, title="Amazon", marketplace="amazon", external_id="fm2")

    resp = await client.get("/internal/products/for-project/proj-1", params={"marketplace": "admitad"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Admitad"


@pytest.mark.asyncio
async def test_for_project_filter_niche(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="Tech", niche="tech", external_id="fn1")
    await _insert_product(db, marketplace_account_id=acc.id, title="Fashion", niche="fashion", external_id="fn2")

    resp = await client.get("/internal/products/for-project/proj-1", params={"niche": "tech"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Tech"


@pytest.mark.asyncio
async def test_for_project_excludes_inactive(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="Active", is_active=True, external_id="ia1")
    await _insert_product(db, marketplace_account_id=acc.id, title="Inactive", is_active=False, external_id="ia2")

    resp = await client.get("/internal/products/for-project/proj-1")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Active"


@pytest.mark.asyncio
async def test_for_project_excludes_out_of_stock(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    await _insert_product(db, marketplace_account_id=acc.id, title="InStock", in_stock=True, external_id="os1")
    await _insert_product(db, marketplace_account_id=acc.id, title="OOS", in_stock=False, external_id="os2")

    resp = await client.get("/internal/products/for-project/proj-1")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "InStock"


# ---------------------------------------------------------------------------
# /internal/products/{product_id}/summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_product_summary(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    p = await _insert_product(db, marketplace_account_id=acc.id)

    resp = await client.get(f"/internal/products/{p.id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == p.id
    assert data["title"] == p.title
    assert data["commission_rate"] == p.commission_rate


@pytest.mark.asyncio
async def test_product_summary_not_found(client: AsyncClient):
    resp = await client.get(f"/internal/products/{uuid.uuid4()}/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_product_summary_no_auth_required(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    p = await _insert_product(db, marketplace_account_id=acc.id)
    # No auth headers
    resp = await client.get(f"/internal/products/{p.id}/summary")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /internal/account-for-product/{product_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_account_for_product(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    campaign = Campaign(
        id=str(uuid.uuid4()),
        marketplace_account_id=acc.id,
        name="Test Camp",
        external_campaign_id="ext-camp-42",
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    p = await _insert_product(
        db,
        marketplace_account_id=acc.id,
        campaign_id=campaign.external_campaign_id,
    )

    resp = await client.get(f"/internal/account-for-product/{p.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == acc.id
    assert data["marketplace"] == "admitad"
    assert data["credentials_encrypted"] == acc.credentials_encrypted
    assert data["campaign_external_id"] == "ext-camp-42"


@pytest.mark.asyncio
async def test_account_for_product_no_campaign(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    p = await _insert_product(db, marketplace_account_id=acc.id, campaign_id=None)

    resp = await client.get(f"/internal/account-for-product/{p.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_external_id"] is None


@pytest.mark.asyncio
async def test_account_for_product_not_found(client: AsyncClient):
    resp = await client.get(f"/internal/account-for-product/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_account_for_product_no_auth_required(client: AsyncClient, db: AsyncSession):
    acc = await _create_account(db)
    p = await _insert_product(db, marketplace_account_id=acc.id)
    resp = await client.get(f"/internal/account-for-product/{p.id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_account_for_product_fallback_campaign_id(client: AsyncClient, db: AsyncSession):
    """When campaign_id doesn't match any campaign, it's used as external_id directly."""
    acc = await _create_account(db)
    p = await _insert_product(
        db,
        marketplace_account_id=acc.id,
        campaign_id="some-external-id-no-match",
    )

    resp = await client.get(f"/internal/account-for-product/{p.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_external_id"] == "some-external-id-no-match"
