"""Unit tests for role-based access control (RBAC) and user scoping."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_admin_rbac_enforcement(client: AsyncClient, db: AsyncSession):
    """Test standard user is forbidden from admin endpoints while admin is granted access."""
    # 1. Create and login standard user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "standard@example.com", "password": "Password123!"},
    )
    user_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "standard@example.com", "password": "Password123!"},
    )
    user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}

    # Standard user attempting /admin/users -> 403 Forbidden
    resp = await client.get("/api/v1/admin/users", headers=user_headers)
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]

    # 2. Create and login Admin user
    admin_user = User.create(
        email="admin@example.com",
        password="AdminPassword123!",
        role=UserRole.ADMIN,
    )
    db.add(admin_user)
    await db.commit()

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Admin user accessing /admin/users -> 200 OK with list of users
    admin_resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert admin_resp.status_code == 200
    user_list = admin_resp.json()
    assert len(user_list) >= 2
    emails = [u["email"] for u in user_list]
    assert "standard@example.com" in emails
    assert "admin@example.com" in emails


@pytest.mark.asyncio
async def test_budget_user_scoping(client: AsyncClient, db: AsyncSession):
    """Test that users cannot access or delete other users' budgets."""
    # 1. User A creates a budget
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user_a@example.com", "password": "Password123!"},
    )
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "user_a@example.com", "password": "Password123!"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    cat_stmt = select(Category).where(Category.slug == "utilities")
    category = (await db.execute(cat_stmt)).scalar_one()

    budget_resp = await client.post(
        "/api/v1/budgets",
        json={
            "category_id": str(category.id),
            "monthly_limit": 5000,
            "period": "2025-01",
        },
        headers=headers_a,
    )
    assert budget_resp.status_code == 201
    budget_id = budget_resp.json()["id"]

    # 2. User B logs in
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user_b@example.com", "password": "Password123!"},
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "user_b@example.com", "password": "Password123!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # User B attempting to GET User A's budget -> 404 Not Found
    get_resp = await client.get(f"/api/v1/budgets/{budget_id}", headers=headers_b)
    assert get_resp.status_code == 404

    # User B attempting to DELETE User A's budget -> 404 Not Found
    del_resp = await client.delete(f"/api/v1/budgets/{budget_id}", headers=headers_b)
    assert del_resp.status_code == 404

    # User A CAN delete their own budget -> 204 No Content
    own_del_resp = await client.delete(f"/api/v1/budgets/{budget_id}", headers=headers_a)
    assert own_del_resp.status_code == 204
