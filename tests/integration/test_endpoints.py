"""Integration tests covering M-Pesa ingestion, budgets CRUD, and observability."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


@pytest.mark.asyncio
async def test_mpesa_ingestion_and_idempotency(client: AsyncClient, db: AsyncSession):
    """Test full M-Pesa ingestion pipeline: normalization, auto-categorization, and duplicate rejection."""
    # 1. Register user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "mpesa_user@example.com",
            "password": "Password123!",
            "full_name": "Bob Mwangi",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "mpesa_user@example.com", "password": "Password123!"},
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Ensure system category "groceries" exists
    cat_stmt = select(Category).where(Category.slug == "groceries")
    cat = (await db.execute(cat_stmt)).scalar_one_or_none()
    assert cat is not None

    # M-Pesa C2B / SMS payload
    payload = {
        "TransID": "QGH7XYZ123",
        "TransAmount": "1500.00",
        "BusinessShortCode": "247247",
        "BillRefNumber": "Naivas Supermarket",
        "MSISDN": "254712345678",
        "TransTime": "20250115143022",
        "FirstName": "John",
    }

    # 2. First ingestion -> 201 Created and auto-categorized as groceries
    resp1 = await client.post("/api/v1/transactions/mpesa", json=payload, headers=headers)
    assert resp1.status_code == 201
    txn_data = resp1.json()
    assert txn_data["ref_code"] == "QGH7XYZ123"
    assert txn_data["amount"] == 1500.0
    assert txn_data["category_id"] == str(cat.id)
    assert txn_data["needs_review"] is False
    assert txn_data["direction"] == "out"

    # 3. Duplicate ingestion -> 409 Conflict
    resp2 = await client.post("/api/v1/transactions/mpesa", json=payload, headers=headers)
    assert resp2.status_code == 409
    assert "Duplicate transaction" in resp2.json()["detail"]

    # 4. Ingestion of ambiguous/unknown payload -> needs_review = True
    unknown_payload = {
        "TransID": "QGH7XYZ999",
        "TransAmount": "750.00",
        "BusinessShortCode": "999999",
        "BillRefNumber": "UnknownMerchant99",
        "MSISDN": "254712345678",
        "TransTime": "20250115150000",
        "FirstName": "Jane",
    }
    resp_unknown = await client.post(
        "/api/v1/transactions/mpesa", json=unknown_payload, headers=headers
    )
    assert resp_unknown.status_code == 201
    unk_data = resp_unknown.json()
    assert unk_data["category_id"] is None
    assert unk_data["needs_review"] is True


@pytest.mark.asyncio
async def test_budget_full_crud(client: AsyncClient, db: AsyncSession):
    """Test full CRUD lifecycle for user budgets."""
    # 1. Register & login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "crud_budget@example.com", "password": "Password123!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "crud_budget@example.com", "password": "Password123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Fetch a category
    cat_stmt = select(Category).where(Category.slug == "utilities")
    category = (await db.execute(cat_stmt)).scalar_one()

    # 2. CREATE
    create_payload = {
        "category_id": str(category.id),
        "monthly_limit": 10000.0,
        "alert_webhook_url": "https://example.com/webhook",
        "period": "2025-01",
    }
    create_resp = await client.post("/api/v1/budgets", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    budget_data = create_resp.json()
    budget_id = budget_data["id"]
    assert budget_data["monthly_limit"] == 10000.0
    assert budget_data["period"] == "2025-01"

    # 3. READ (List)
    list_resp = await client.get("/api/v1/budgets", headers=headers)
    assert list_resp.status_code == 200
    budgets = list_resp.json()
    assert len(budgets) == 1
    assert budgets[0]["id"] == budget_id

    # 4. READ (Single)
    get_resp = await client.get(f"/api/v1/budgets/{budget_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == budget_id

    # 5. UPDATE (PATCH)
    update_payload = {"monthly_limit": 15000.0}
    patch_resp = await client.patch(
        f"/api/v1/budgets/{budget_id}", json=update_payload, headers=headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["monthly_limit"] == 15000.0

    # 6. DELETE
    del_resp = await client.delete(f"/api/v1/budgets/{budget_id}", headers=headers)
    assert del_resp.status_code == 204

    # 7. Verify deletion
    verify_resp = await client.get(f"/api/v1/budgets/{budget_id}", headers=headers)
    assert verify_resp.status_code == 404


@pytest.mark.asyncio
async def test_observability_health_and_request_id(client: AsyncClient):
    """Test health check and Request ID middleware propagation."""
    # Health check
    health_resp = await client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
    assert "X-Request-ID" in health_resp.headers

    # Custom request ID preserved
    custom_id = "test-custom-request-id-12345"
    resp = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == custom_id
