"""Unit tests for authentication, JWT lifecycle, and refresh token rotation."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_refresh_token, get_password_hash, hash_token, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    """Test full registration and login lifecycle."""
    # 1. Successful registration
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "StrongPassword123!",
            "full_name": "Alice Wanjiku",
        },
    )
    assert register_resp.status_code == 201
    data = register_resp.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data

    # 2. Duplicate registration rejected
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "AnotherPassword123!",
            "full_name": "Alice Duplicate",
        },
    )
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"]

    # 3. Weak password rejected (< 8 chars)
    weak_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "password": "short",
        },
    )
    assert weak_resp.status_code == 422

    # 4. Successful login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

    # 5. Invalid credentials login
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 6. Nonexistent user login
    notfound_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Password123!"},
    )
    assert notfound_login.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client: AsyncClient):
    """Test refresh token rotation: old revoked, new issued, replay attacks rejected."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "rotation@example.com", "password": "StrongPassword123!"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "rotation@example.com", "password": "StrongPassword123!"},
    )
    tokens = login_resp.json()
    first_refresh = tokens["refresh_token"]

    # 1. Rotate refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != first_refresh
    second_refresh = new_tokens["refresh_token"]

    # 2. Replay of old refresh token must be rejected
    replay_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert replay_resp.status_code == 401

    # 3. Logout using the second refresh token
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": second_refresh},
    )
    assert logout_resp.status_code == 204

    # 4. Using revoked token must fail
    after_logout_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert after_logout_resp.status_code == 401

    # 5. Invalid / garbage token must fail
    garbage_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not.a.valid.jwt.token"},
    )
    assert garbage_resp.status_code == 401

    # 6. Access token cannot be used as a refresh token
    access_as_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert access_as_refresh.status_code == 401


@pytest.mark.asyncio
async def test_expired_refresh_token_is_revoked(client: AsyncClient, db: AsyncSession):
    """A refresh token past DB expiry is rejected and marked revoked."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "expired@example.com", "password": "StrongPassword123!"},
    )
    user = (await db.execute(select(User).where(User.email == "expired@example.com"))).scalar_one()
    raw = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            revoked=False,
        )
    )
    await db.commit()

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw})
    assert resp.status_code == 401


def test_password_hash_roundtrip_and_invalid_hash():
    """Bcrypt hashes verify; malformed hashes fail closed."""
    hashed = get_password_hash("StrongPassword123!")
    assert verify_password("StrongPassword123!", hashed) is True
    assert verify_password("wrong-password", hashed) is False
    assert verify_password("anything", "not-a-bcrypt-hash") is False
