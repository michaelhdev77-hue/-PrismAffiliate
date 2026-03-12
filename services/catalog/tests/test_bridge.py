"""Tests for /api/v1/bridge/ endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bridge_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/bridge/push-to-prism", json={"max_products": 5})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# push-to-prism
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_push_to_prism(client: AsyncClient, auth_headers: dict):
    mock_result = MagicMock()
    mock_result.id = "fake-task-id-123"

    with patch("app.routes.bridge._celery") as mock_celery:
        mock_celery.send_task.return_value = mock_result

        resp = await client.post(
            "/api/v1/bridge/push-to-prism",
            headers=auth_headers,
            json={"prism_project_id": "proj-abc", "max_products": 10},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["task_id"] == "fake-task-id-123"

    mock_celery.send_task.assert_called_once_with(
        "affiliate.push_products_to_prism",
        kwargs={"prism_project_id": "proj-abc", "max_products": 10},
    )


@pytest.mark.asyncio
async def test_push_to_prism_defaults(client: AsyncClient, auth_headers: dict):
    """Test with default values (no prism_project_id, max_products=10)."""
    mock_result = MagicMock()
    mock_result.id = "task-default"

    with patch("app.routes.bridge._celery") as mock_celery:
        mock_celery.send_task.return_value = mock_result

        resp = await client.post(
            "/api/v1/bridge/push-to-prism",
            headers=auth_headers,
            json={},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"

    mock_celery.send_task.assert_called_once_with(
        "affiliate.push_products_to_prism",
        kwargs={"prism_project_id": None, "max_products": 10},
    )


@pytest.mark.asyncio
async def test_push_to_prism_custom_max(client: AsyncClient, auth_headers: dict):
    mock_result = MagicMock()
    mock_result.id = "task-custom"

    with patch("app.routes.bridge._celery") as mock_celery:
        mock_celery.send_task.return_value = mock_result

        resp = await client.post(
            "/api/v1/bridge/push-to-prism",
            headers=auth_headers,
            json={"max_products": 50},
        )

    assert resp.status_code == 200
    mock_celery.send_task.assert_called_once_with(
        "affiliate.push_products_to_prism",
        kwargs={"prism_project_id": None, "max_products": 50},
    )
