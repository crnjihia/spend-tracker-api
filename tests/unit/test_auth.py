"""Unit tests for authentication, JWT lifecycle, and refresh token rotation."""

import pytest
from httpx import AsyncClient


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
