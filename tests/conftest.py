"""Test configuration and async fixtures for pytest."""
# ruff: noqa: E402

import asyncio
import os
import sys
from typing import AsyncGenerator

# Set environment variables for testing BEFORE importing application modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-min-32-chars-long-1234567890"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["RATE_LIMIT"] = "10000/minute"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.models  # noqa: F401
from app.core.deps import get_db
from app.core.redis import set_redis
from app.db.base import Base
from app.db.seed import seed_categories
from app.db.session import async_engine
from app.main import app as fastapi_app


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create database tables once for the test session."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def fake_redis_client():
    """Provide an in-memory asynchronous fakeredis client for testing."""
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    set_redis(fake_redis)
    yield fake_redis
    await fake_redis.flushall()
    await fake_redis.aclose()
    set_redis(None)


@pytest_asyncio.fixture
async def db(
    fake_redis_client,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session with pre-seeded categories for each test."""
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        # Seed categories if not already populated
        await seed_categories(session)
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient configured with overridden get_db dependency."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
