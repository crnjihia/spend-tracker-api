"""Unit tests for spending analytics and summary reports."""

import datetime
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection
from app.models.user import User


@pytest.mark.asyncio
async def test_summary_report_generation(client: AsyncClient, db: AsyncSession):
    """Test calculation of category totals, top merchants, MoM delta, and daily series."""
    # 1. Register & login
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "reports_user@example.com", "password": "StrongPassword123!"},
    )
    user_id = reg_resp.json()["id"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "reports_user@example.com", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Fetch user's account and categories from DB
    user = await db.get(User, uuid.UUID(user_id))
    assert user is not None
    account = user.accounts[0]

    cat_groceries = (
        await db.execute(select(Category).where(Category.slug == "groceries"))
    ).scalar_one()
    cat_utilities = (
        await db.execute(select(Category).where(Category.slug == "utilities"))
    ).scalar_one()

    # 2. Add current period transactions (Jan 2025)
    txns = [
        Transaction(
            account_id=account.id,
            amount=Decimal("4000.00"),
            category_id=cat_groceries.id,
            merchant="Naivas",
            ref_code="REP001",
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2025, 1, 5, 12, 0, 0, tzinfo=datetime.timezone.utc),
            raw_payload={},
        ),
        Transaction(
            account_id=account.id,
            amount=Decimal("2000.00"),
            category_id=cat_groceries.id,
            merchant="Quickmart",
            ref_code="REP002",
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2025, 1, 10, 15, 0, 0, tzinfo=datetime.timezone.utc),
            raw_payload={},
        ),
        Transaction(
            account_id=account.id,
            amount=Decimal("1500.00"),
            category_id=cat_utilities.id,
            merchant="KPLC Prepaid",
            ref_code="REP003",
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2025, 1, 10, 16, 0, 0, tzinfo=datetime.timezone.utc),
            raw_payload={},
        ),
        # Prior month transaction (Dec 2024: 5000 total)
        Transaction(
            account_id=account.id,
            amount=Decimal("5000.00"),
            category_id=cat_groceries.id,
            merchant="Naivas",
            ref_code="REP004",
            direction=TransactionDirection.OUT,
            occurred_at=datetime.datetime(2024, 12, 15, 10, 0, 0, tzinfo=datetime.timezone.utc),
            raw_payload={},
        ),
    ]
    db.add_all(txns)
    await db.commit()

    # 3. Request summary report
    resp = await client.get(
        "/api/v1/reports/summary?from=2025-01-01&to=2025-01-31", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["from_date"] == "2025-01-01"
    assert data["to_date"] == "2025-01-31"

    # Category totals
    assert data["totals_by_category"]["groceries"] == 6000.0
    assert data["totals_by_category"]["utilities"] == 1500.0

    # Top merchants
    top_merchants = {m["merchant"]: m["amount"] for m in data["top_merchants"]}
    assert top_merchants["Naivas"] == 4000.0
    assert top_merchants["Quickmart"] == 2000.0
    assert top_merchants["KPLC Prepaid"] == 1500.0

    # Month-over-Month Delta (Current 7500 - Prior 5000 = +2500)
    assert data["month_over_month_delta"] == 2500.0

    # Daily spend series
    daily_map = {d["date"]: d["amount"] for d in data["daily_spend_series"]}
    assert daily_map["2025-01-05"] == 4000.0
    assert daily_map["2025-01-10"] == 3500.0


@pytest.mark.asyncio
async def test_summary_report_date_validation(client: AsyncClient):
    """Test date validations: from > to, and missing params."""
    # Register & login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "date_user@example.com", "password": "StrongPassword123!"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "date_user@example.com", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # from > to should return 400
    bad_dates = await client.get(
        "/api/v1/reports/summary?from=2025-02-01&to=2025-01-01", headers=headers
    )
    assert bad_dates.status_code == 400

    # missing params should return 400
    missing = await client.get("/api/v1/reports/summary", headers=headers)
    assert missing.status_code == 400


@pytest.mark.asyncio
async def test_root_and_invalid_budget_period(client: AsyncClient):
    """Smoke-test root metadata and budget period validation."""
    root = await client.get("/")
    assert root.status_code == 200
    assert root.json()["name"]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "period_user@example.com", "password": "StrongPassword123!"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "period_user@example.com", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    bad_period = await client.post(
        "/api/v1/budgets",
        json={
            "category_id": "00000000-0000-0000-0000-000000000000",
            "monthly_limit": 1000,
            "period": "2025/01",
        },
        headers=headers,
    )
    assert bad_period.status_code == 422
