"""
Root conftest for catalog service tests.
Sets environment variables BEFORE any app imports to avoid real DB connections.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_catalog.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ENCRYPTION_KEY"] = "HywPLm1915qzgvOyDtwUOqQbBNxKOfS8ogKtj0Ja8aM="
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db import Base, get_db
from app.deps import require_auth
from app.main import app


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite://"  # in-memory

_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """Create all tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Provide a direct async DB session for test helpers."""
    async with _TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _make_token(payload: dict | None = None) -> str:
    data = payload or {"sub": str(uuid.uuid4()), "role": "admin"}
    return jwt.encode(data, os.environ["SECRET_KEY"], algorithm="HS256")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token()}"}


# ---------------------------------------------------------------------------
# Override app dependencies
# ---------------------------------------------------------------------------

async def _override_get_db():
    async with _TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
