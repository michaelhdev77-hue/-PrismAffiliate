"""
Root conftest for the links service tests.

Sets environment variables BEFORE any app module is imported,
then provides async DB session, httpx client, and auth fixtures.
"""
import os

# ── Override env vars before any app import ──────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_links.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0xMjM0NTY3ODkwYWJj"  # base64 placeholder
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["CATALOG_SERVICE_URL"] = "http://mock-catalog:8011"

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Generate a real Fernet key and put it in env (must happen before app.config is loaded)
_fernet_key = Fernet.generate_key().decode()
os.environ["ENCRYPTION_KEY"] = _fernet_key

# Now it's safe to import app modules
from app.db import Base, get_db
from app.main import app


# ── Async engine for tests (SQLite) ─────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_links.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Clean up the file
    if os.path.exists("test_links.db"):
        try:
            os.remove("test_links.db")
        except OSError:
            pass


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid JWT."""
    payload = {
        "sub": "test-user-id",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
