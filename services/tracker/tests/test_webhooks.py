import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx
from sqlalchemy import select

from app.models import ConversionEvent


pytestmark = pytest.mark.asyncio


def _mock_link_data(
    link_id: str = "link-001",
    product_id: str = "prod-001",
    prism_content_id: str = "content-001",
    prism_project_id: str = "project-001",
    marketplace_account_id: str = "account-001",
):
    """Create a mock httpx.Response for the links service by-subid call."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "id": link_id,
        "product_id": product_id,
        "prism_content_id": prism_content_id,
        "prism_project_id": prism_project_id,
        "marketplace_account_id": marketplace_account_id,
    }
    return response


def _mock_link_404():
    response = MagicMock(spec=httpx.Response)
    response.status_code = 404
    response.json.return_value = {"detail": "Not found"}
    return response


# ---------------------------------------------------------------------------
# Admitad webhook
# ---------------------------------------------------------------------------

class TestAdmitadWebhook:
    async def test_admitad_postback_with_subid(self, async_client, db):
        order_id = f"adm-order-{uuid.uuid4().hex[:8]}"
        subid = "sub-track-123"

        mock_resp = _mock_link_data(
            link_id="link-adm-001",
            product_id="prod-adm-001",
            prism_content_id="cnt-adm-001",
            prism_project_id="prj-adm-001",
            marketplace_account_id="acc-adm-001",
        )

        with patch("app.routes.webhooks.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.post(
                "/internal/webhooks/admitad",
                json={
                    "order_id": order_id,
                    "order_sum": 1500.0,
                    "payment_sum": 150.0,
                    "currency": "RUB",
                    "action": "sale",
                    "subid": subid,
                    "advcampaign_id": "camp-123",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()

        assert event.marketplace == "admitad"
        assert event.order_amount == 1500.0
        assert event.commission_amount == 150.0
        assert event.currency == "RUB"
        assert event.conversion_status == "pending"
        assert event.affiliate_link_id == "link-adm-001"
        assert event.product_id == "prod-adm-001"
        assert event.prism_content_id == "cnt-adm-001"
        assert event.prism_project_id == "prj-adm-001"
        assert event.marketplace_account_id == "acc-adm-001"

    async def test_admitad_postback_without_subid(self, async_client, db):
        order_id = f"adm-nosub-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/admitad",
            json={
                "order_id": order_id,
                "order_sum": 500.0,
                "payment_sum": 50.0,
                "currency": "USD",
            },
        )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()

        assert event.marketplace == "admitad"
        assert event.order_amount == 500.0
        assert event.commission_amount == 50.0
        assert event.currency == "USD"
        assert event.affiliate_link_id is None
        assert event.product_id is None

    async def test_admitad_postback_subid_resolve_fails(self, async_client, db):
        """When the links service is unreachable, the event is still stored."""
        order_id = f"adm-fail-{uuid.uuid4().hex[:8]}"

        with patch("app.routes.webhooks.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.post(
                "/internal/webhooks/admitad",
                json={
                    "order_id": order_id,
                    "order_sum": 200.0,
                    "payment_sum": 20.0,
                    "subid": "broken-sub",
                },
            )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()
        assert event.marketplace == "admitad"
        assert event.order_amount == 200.0
        assert event.affiliate_link_id is None

    async def test_admitad_postback_subid_not_found(self, async_client, db):
        """When the links service returns 404 for subid, event is still stored."""
        order_id = f"adm-404-{uuid.uuid4().hex[:8]}"
        mock_resp = _mock_link_404()

        with patch("app.routes.webhooks.httpx.AsyncClient") as mock_client_cls:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client_instance

            resp = await async_client.post(
                "/internal/webhooks/admitad",
                json={
                    "order_id": order_id,
                    "order_sum": 300.0,
                    "payment_sum": 30.0,
                    "subid": "unknown-sub",
                },
            )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()
        assert event.marketplace == "admitad"
        assert event.affiliate_link_id is None

    async def test_admitad_defaults_for_missing_fields(self, async_client, db):
        order_id = f"adm-defaults-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/admitad",
            json={"order_id": order_id},
        )
        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()
        assert event.order_amount == 0.0
        assert event.commission_amount == 0.0
        assert event.currency == "RUB"


# ---------------------------------------------------------------------------
# Amazon webhook
# ---------------------------------------------------------------------------

class TestAmazonWebhook:
    async def test_amazon_postback(self, async_client, db):
        order_id = f"amz-order-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/amazon",
            json={
                "orderId": order_id,
                "orderTotal": 99.99,
                "commission": 5.50,
                "currency": "USD",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()

        assert event.marketplace == "amazon"
        assert event.order_amount == pytest.approx(99.99)
        assert event.commission_amount == pytest.approx(5.50)
        assert event.currency == "USD"
        assert event.conversion_status == "pending"

    async def test_amazon_postback_defaults(self, async_client, db):
        """When fields are missing, defaults are used."""
        resp = await async_client.post(
            "/internal/webhooks/amazon",
            json={},
        )

        assert resp.status_code == 200

        result = await db.execute(select(ConversionEvent).where(ConversionEvent.marketplace == "amazon"))
        event = result.scalar_one()

        assert event.order_amount == 0.0
        assert event.commission_amount == 0.0
        assert event.currency == "USD"

    async def test_amazon_postback_with_product_id(self, async_client, db):
        order_id = f"amz-prod-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/amazon",
            json={
                "orderId": order_id,
                "orderTotal": 49.99,
                "commission": 2.50,
                "currency": "EUR",
                "productId": "B08XYZ123",
            },
        )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()
        assert event.marketplace == "amazon"
        assert event.currency == "EUR"


# ---------------------------------------------------------------------------
# Generic marketplace webhook
# ---------------------------------------------------------------------------

class TestGenericWebhook:
    async def test_generic_postback(self, async_client, db):
        order_id = f"gen-order-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/ebay",
            json={
                "order_id": order_id,
                "amount": 75.00,
                "commission": 3.75,
                "currency": "GBP",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()

        assert event.marketplace == "ebay"
        assert event.order_amount == pytest.approx(75.00)
        assert event.commission_amount == pytest.approx(3.75)
        assert event.currency == "GBP"
        assert event.conversion_status == "pending"

    async def test_generic_postback_unknown_marketplace(self, async_client, db):
        order_id = f"custom-order-{uuid.uuid4().hex[:8]}"

        resp = await async_client.post(
            "/internal/webhooks/my_custom_shop",
            json={
                "order_id": order_id,
                "amount": 120.00,
                "commission": 12.00,
                "currency": "USD",
            },
        )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.order_id == order_id)
        )
        event = result.scalar_one()
        assert event.marketplace == "my_custom_shop"

    async def test_generic_postback_defaults(self, async_client, db):
        resp = await async_client.post(
            "/internal/webhooks/aliexpress",
            json={},
        )

        assert resp.status_code == 200

        result = await db.execute(
            select(ConversionEvent).where(ConversionEvent.marketplace == "aliexpress")
        )
        event = result.scalar_one()
        assert event.order_amount == 0.0
        assert event.commission_amount == 0.0
        assert event.currency == "USD"

    async def test_generic_multiple_marketplaces(self, async_client, db):
        """Verify different marketplace path params are stored correctly."""
        for mp in ["rakuten", "cj_affiliate", "awin"]:
            order_id = f"{mp}-{uuid.uuid4().hex[:8]}"
            resp = await async_client.post(
                f"/internal/webhooks/{mp}",
                json={
                    "order_id": order_id,
                    "amount": 50.0,
                    "commission": 5.0,
                    "currency": "USD",
                },
            )
            assert resp.status_code == 200

        result = await db.execute(select(ConversionEvent))
        events = result.scalars().all()
        marketplaces = {e.marketplace for e in events}
        assert marketplaces == {"rakuten", "cj_affiliate", "awin"}
