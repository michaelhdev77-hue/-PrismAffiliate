"""Tests for /api/v1/products/ endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(**overrides) -> dict:
    defaults = {
        "id": str(uuid.uuid4()),
        "marketplace": "admitad",
        "marketplace_account_id": str(uuid.uuid4()),
        "external_id": str(uuid.uuid4()),
        "title": "Test Product",
        "description": "A good product",
        "category": "Electronics",
        "brand": "TestBrand",
        "price": 99.99,
        "currency": "RUB",
        "original_price": 129.99,
        "discount_pct": 23.0,
        "image_url": "https://example.com/img.jpg",
        "product_url": "https://example.com/product",
        "rating": 4.5,
        "review_count": 100,
        "in_stock": True,
        "commission_rate": 5.0,
        "commission_type": "percentage",
        "tags": ["gadget", "sale"],
        "niche": "tech",
        "campaign_id": str(uuid.uuid4()),
        "feed_id": str(uuid.uuid4()),
        "is_active": True,
    }
    defaults.update(overrides)
    return defaults


async def _insert_product(db: AsyncSession, **overrides) -> Product:
    data = _make_product(**overrides)
    p = Product(**data)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Tests — search / list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_products_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/products/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["pages"] == 1


@pytest.mark.asyncio
async def test_list_products_returns_items(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="Alpha")
    await _insert_product(db, title="Beta", external_id="ext-beta")

    resp = await client.get("/api/v1/products/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_search_by_query(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="Wireless Headphones", external_id="wh-1")
    await _insert_product(db, title="USB Cable", external_id="usb-1")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"q": "wireless"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Wireless Headphones"


@pytest.mark.asyncio
async def test_filter_by_category(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="A", category="Clothing", external_id="c1")
    await _insert_product(db, title="B", category="Electronics", external_id="c2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"category": "clothing"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "Clothing"


@pytest.mark.asyncio
async def test_filter_by_marketplace(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="A", marketplace="amazon", external_id="m1")
    await _insert_product(db, title="B", marketplace="ebay", external_id="m2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"marketplace": "amazon"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["marketplace"] == "amazon"


@pytest.mark.asyncio
async def test_filter_by_campaign_id(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    cid = str(uuid.uuid4())
    await _insert_product(db, title="A", campaign_id=cid, external_id="ca1")
    await _insert_product(db, title="B", external_id="ca2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"campaign_id": cid})
    body = resp.json()
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_filter_has_image(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="WithImg", image_url="https://img.com/1.jpg", external_id="img1")
    await _insert_product(db, title="NoImg", image_url="", external_id="img2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"has_image": True})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "WithImg"


@pytest.mark.asyncio
async def test_filter_min_commission(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="Low", commission_rate=1.0, external_id="mc1")
    await _insert_product(db, title="High", commission_rate=10.0, external_id="mc2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"min_commission": 5.0})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "High"


@pytest.mark.asyncio
async def test_sort_by_score(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    # score = commission_rate*0.5 + rating*0.3 + discount_pct*0.2
    # p1: 10*0.5 + 5*0.3 + 50*0.2 = 5+1.5+10 = 16.5
    # p2: 2*0.5 + 3*0.3 + 0*0.2 = 1+0.9+0 = 1.9
    await _insert_product(db, title="High Score", commission_rate=10.0, rating=5.0, discount_pct=50.0, external_id="s1")
    await _insert_product(db, title="Low Score", commission_rate=2.0, rating=3.0, discount_pct=0.0, external_id="s2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"sort": "score"})
    body = resp.json()
    assert body["items"][0]["title"] == "High Score"
    assert body["items"][1]["title"] == "Low Score"


@pytest.mark.asyncio
async def test_sort_by_price(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="Expensive", price=500.0, external_id="pr1")
    await _insert_product(db, title="Cheap", price=10.0, external_id="pr2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"sort": "price"})
    body = resp.json()
    assert body["items"][0]["title"] == "Cheap"


@pytest.mark.asyncio
async def test_sort_by_rating(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="BestRated", rating=5.0, external_id="r1")
    await _insert_product(db, title="WorstRated", rating=1.0, external_id="r2")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"sort": "rating"})
    body = resp.json()
    assert body["items"][0]["title"] == "BestRated"


# ---------------------------------------------------------------------------
# Tests — pagination
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    for i in range(25):
        await _insert_product(db, title=f"Product {i}", external_id=f"pag-{i}")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"page": 1, "per_page": 10})
    body = resp.json()
    assert body["total"] == 25
    assert body["page"] == 1
    assert body["pages"] == 3
    assert len(body["items"]) == 10

    resp2 = await client.get("/api/v1/products/", headers=auth_headers, params={"page": 3, "per_page": 10})
    body2 = resp2.json()
    assert len(body2["items"]) == 5
    assert body2["page"] == 3


# ---------------------------------------------------------------------------
# Tests — categories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, category="Books", external_id="cat1")
    await _insert_product(db, category="Electronics", external_id="cat2")
    await _insert_product(db, category="Books", external_id="cat3")

    resp = await client.get("/api/v1/products/categories", headers=auth_headers)
    assert resp.status_code == 200
    cats = resp.json()
    assert "Books" in cats
    assert "Electronics" in cats
    assert len(cats) == 2


@pytest.mark.asyncio
async def test_list_categories_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/products/categories")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — get single product
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    p = await _insert_product(db)
    resp = await client.get(f"/api/v1/products/{p.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == p.id
    assert resp.json()["title"] == p.title


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/products/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_product_requires_auth(client: AsyncClient, db: AsyncSession):
    p = await _insert_product(db)
    resp = await client.get(f"/api/v1/products/{p.id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — inactive / out-of-stock filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inactive_products_excluded(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="Active", is_active=True, external_id="act1")
    await _insert_product(db, title="Inactive", is_active=False, external_id="act2")

    resp = await client.get("/api/v1/products/", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Active"


@pytest.mark.asyncio
async def test_out_of_stock_excluded_by_default(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="InStock", in_stock=True, external_id="st1")
    await _insert_product(db, title="OutOfStock", in_stock=False, external_id="st2")

    resp = await client.get("/api/v1/products/", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_out_of_stock_included_when_flag_false(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await _insert_product(db, title="InStock", in_stock=True, external_id="st3")
    await _insert_product(db, title="OutOfStock", in_stock=False, external_id="st4")

    resp = await client.get("/api/v1/products/", headers=auth_headers, params={"in_stock_only": False})
    body = resp.json()
    assert body["total"] == 2
