import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AffiliateStats


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stat(
    stat_date: date,
    marketplace: str = "admitad",
    product_id: str | None = None,
    prism_project_id: str | None = None,
    prism_content_id: str | None = None,
    clicks: int = 10,
    conversions: int = 2,
    revenue: float = 100.0,
    commission: float = 10.0,
) -> AffiliateStats:
    return AffiliateStats(
        id=str(uuid.uuid4()),
        stat_date=stat_date,
        marketplace=marketplace,
        product_id=product_id,
        prism_project_id=prism_project_id,
        prism_content_id=prism_content_id,
        clicks=clicks,
        conversions=conversions,
        revenue=revenue,
        commission=commission,
    )


async def _seed_stats(db: AsyncSession, stats: list[AffiliateStats]):
    for s in stats:
        db.add(s)
    await db.commit()


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestAuthRequired:
    """All analytics endpoints require a valid JWT."""

    async def test_overview_no_auth(self, async_client):
        resp = await async_client.get("/api/v1/analytics/overview")
        assert resp.status_code == 401

    async def test_by_marketplace_no_auth(self, async_client):
        resp = await async_client.get("/api/v1/analytics/by-marketplace")
        assert resp.status_code == 401

    async def test_by_product_no_auth(self, async_client):
        resp = await async_client.get("/api/v1/analytics/by-product")
        assert resp.status_code == 401

    async def test_by_project_no_auth(self, async_client):
        resp = await async_client.get("/api/v1/analytics/by-project")
        assert resp.status_code == 401

    async def test_invalid_token(self, async_client):
        resp = await async_client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class TestOverview:
    async def test_empty_db_returns_zeros(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_clicks"] == 0
        assert data["total_conversions"] == 0
        assert data["total_revenue"] == 0
        assert data["total_commission"] == 0
        assert data["period_days"] == 30

    async def test_aggregation(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, clicks=10, conversions=2, revenue=100.0, commission=10.0),
            _make_stat(today - timedelta(days=1), marketplace="amazon", clicks=20, conversions=3, revenue=200.0, commission=25.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_clicks"] == 30
        assert data["total_conversions"] == 5
        assert data["total_revenue"] == pytest.approx(300.0)
        assert data["total_commission"] == pytest.approx(35.0)

    async def test_period_filtering(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, clicks=10, conversions=1, revenue=50.0, commission=5.0),
            _make_stat(today - timedelta(days=60), clicks=100, conversions=20, revenue=1000.0, commission=100.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/overview?period=30", headers=auth_headers)
        data = resp.json()
        assert data["total_clicks"] == 10
        assert data["total_conversions"] == 1
        assert data["total_revenue"] == pytest.approx(50.0)
        assert data["total_commission"] == pytest.approx(5.0)
        assert data["period_days"] == 30

    async def test_custom_period(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today - timedelta(days=5), clicks=5, conversions=1, revenue=25.0, commission=2.5),
            _make_stat(today - timedelta(days=15), clicks=15, conversions=3, revenue=75.0, commission=7.5),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/overview?period=7", headers=auth_headers)
        data = resp.json()
        assert data["total_clicks"] == 5
        assert data["total_conversions"] == 1
        assert data["period_days"] == 7


# ---------------------------------------------------------------------------
# By-marketplace
# ---------------------------------------------------------------------------

class TestByMarketplace:
    async def test_empty_db_returns_empty_list(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/analytics/by-marketplace", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_groups_by_marketplace(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, marketplace="admitad", clicks=10, conversions=1, revenue=100.0, commission=10.0),
            _make_stat(today - timedelta(days=1), marketplace="admitad", clicks=5, conversions=1, revenue=50.0, commission=5.0),
            _make_stat(today, marketplace="amazon", clicks=20, conversions=5, revenue=500.0, commission=50.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-marketplace", headers=auth_headers)
        data = resp.json()
        assert len(data) == 2

        # Sorted by revenue desc => amazon first
        assert data[0]["dimension"] == "amazon"
        assert data[0]["clicks"] == 20
        assert data[0]["revenue"] == pytest.approx(500.0)

        assert data[1]["dimension"] == "admitad"
        assert data[1]["clicks"] == 15
        assert data[1]["revenue"] == pytest.approx(150.0)

    async def test_period_filtering(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, marketplace="admitad", clicks=10, revenue=100.0, commission=10.0),
            _make_stat(today - timedelta(days=60), marketplace="amazon", clicks=50, revenue=1000.0, commission=100.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-marketplace?period=30", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["dimension"] == "admitad"


# ---------------------------------------------------------------------------
# By-product
# ---------------------------------------------------------------------------

class TestByProduct:
    async def test_empty_db_returns_empty_list(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/analytics/by-product", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_groups_by_product(self, async_client, auth_headers, db):
        today = date.today()
        pid1 = str(uuid.uuid4())
        pid2 = str(uuid.uuid4())
        stats = [
            _make_stat(today, product_id=pid1, clicks=10, revenue=200.0, commission=20.0),
            _make_stat(today - timedelta(days=1), product_id=pid1, clicks=5, revenue=100.0, commission=10.0),
            _make_stat(today, product_id=pid2, clicks=30, revenue=500.0, commission=50.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-product", headers=auth_headers)
        data = resp.json()
        assert len(data) == 2
        # Sorted by revenue desc => pid2 first
        assert data[0]["dimension"] == pid2
        assert data[0]["revenue"] == pytest.approx(500.0)
        assert data[1]["dimension"] == pid1
        assert data[1]["revenue"] == pytest.approx(300.0)

    async def test_excludes_null_product_id(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, product_id=None, clicks=100, revenue=9999.0, commission=999.0),
            _make_stat(today, product_id=str(uuid.uuid4()), clicks=1, revenue=10.0, commission=1.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-product", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1

    async def test_limit(self, async_client, auth_headers, db):
        today = date.today()
        # Create 25 products
        stats = [
            _make_stat(
                today,
                product_id=str(uuid.uuid4()),
                marketplace=f"mp_{i}",
                clicks=i,
                revenue=float(i * 10),
                commission=float(i),
            )
            for i in range(25)
        ]
        await _seed_stats(db, stats)

        # Default limit is 20
        resp = await async_client.get("/api/v1/analytics/by-product", headers=auth_headers)
        data = resp.json()
        assert len(data) == 20

    async def test_period_filtering(self, async_client, auth_headers, db):
        today = date.today()
        pid_recent = str(uuid.uuid4())
        pid_old = str(uuid.uuid4())
        stats = [
            _make_stat(today, product_id=pid_recent, clicks=5, revenue=50.0, commission=5.0),
            _make_stat(today - timedelta(days=60), product_id=pid_old, clicks=50, revenue=500.0, commission=50.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-product?period=30", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["dimension"] == pid_recent


# ---------------------------------------------------------------------------
# By-project
# ---------------------------------------------------------------------------

class TestByProject:
    async def test_empty_db_returns_empty_list(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/analytics/by-project", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_groups_by_project(self, async_client, auth_headers, db):
        today = date.today()
        proj1 = str(uuid.uuid4())
        proj2 = str(uuid.uuid4())
        stats = [
            _make_stat(today, prism_project_id=proj1, clicks=10, revenue=100.0, commission=10.0),
            _make_stat(today - timedelta(days=1), prism_project_id=proj1, marketplace="amazon", clicks=5, revenue=50.0, commission=5.0),
            _make_stat(today, prism_project_id=proj2, clicks=30, revenue=800.0, commission=80.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-project", headers=auth_headers)
        data = resp.json()
        assert len(data) == 2
        assert data[0]["dimension"] == proj2
        assert data[0]["revenue"] == pytest.approx(800.0)
        assert data[1]["dimension"] == proj1
        assert data[1]["clicks"] == 15

    async def test_excludes_null_project_id(self, async_client, auth_headers, db):
        today = date.today()
        stats = [
            _make_stat(today, prism_project_id=None, clicks=100, revenue=9999.0, commission=999.0),
            _make_stat(today, prism_project_id=str(uuid.uuid4()), clicks=1, revenue=10.0, commission=1.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-project", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1

    async def test_period_filtering(self, async_client, auth_headers, db):
        today = date.today()
        proj_recent = str(uuid.uuid4())
        proj_old = str(uuid.uuid4())
        stats = [
            _make_stat(today, prism_project_id=proj_recent, clicks=5, revenue=50.0, commission=5.0),
            _make_stat(today - timedelta(days=60), prism_project_id=proj_old, clicks=50, revenue=500.0, commission=50.0),
        ]
        await _seed_stats(db, stats)

        resp = await async_client.get("/api/v1/analytics/by-project?period=7", headers=auth_headers)
        data = resp.json()
        assert len(data) == 1
        assert data[0]["dimension"] == proj_recent


# ---------------------------------------------------------------------------
# Health endpoint (no auth required)
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_health(self, async_client):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "analytics"
