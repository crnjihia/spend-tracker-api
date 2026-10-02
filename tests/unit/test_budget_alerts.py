"""Unit tests for budget tracking and idempotent webhook alerts."""

import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection
from app.models.user import User
from app.services.budget_alerts import BudgetAlertService


@pytest.mark.asyncio
async def test_budget_alert_firing_and_idempotency(db: AsyncSession, monkeypatch):
    """Test budget alert triggers webhook on limit exceedance and is idempotent via Redis."""
    # 1. Setup user, account, budget
    user = User.create(email="budget_test@example.com", password="StrongPassword123!")
    db.add(user)
    await db.flush()

    account = Account(
        user_id=user.id,
        name="M-Pesa Test",
        type=AccountType.MPESA,
        balance=Decimal("20000.00"),
        currency="KES",
    )
    db.add(account)

    cat_stmt = select(Category).where(Category.slug == "groceries")
    category = (await db.execute(cat_stmt)).scalar_one()

    budget = Budget(
        user_id=user.id,
        category_id=category.id,
        monthly_limit=Decimal("5000.00"),
        alert_webhook_url="https://webhook.site/test-alert",
        period="2025-01",
    )
    db.add(budget)
    await db.commit()

    # Track webhook calls
    webhook_dispatches = []

    async def mock_post(self, url, json=None, timeout=None):
        webhook_dispatches.append((url, json))

        class MockResp:
            status_code = 200

        return MockResp()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    alert_service = BudgetAlertService(db)

    # 2. Transaction 1: 3000 KES (under 5000 limit) -> No alert
    txn1 = Transaction(
        account_id=account.id,
        amount=Decimal("3000.00"),
        category_id=category.id,
        merchant="Naivas",
        ref_code="TXN001",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.datetime(2025, 1, 10, 10, 0, 0, tzinfo=datetime.timezone.utc),
        raw_payload={},
    )
    db.add(txn1)
    await db.commit()

    fired1 = await alert_service.maybe_send_alert(txn1)
    assert fired1 is False
    assert len(webhook_dispatches) == 0

    # 3. Transaction 2: 3000 KES (Total 6000 > 5000 limit) -> Fires webhook!
    txn2 = Transaction(
        account_id=account.id,
        amount=Decimal("3000.00"),
        category_id=category.id,
        merchant="Naivas",
        ref_code="TXN002",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc),
        raw_payload={},
    )
    db.add(txn2)
    await db.commit()

    fired2 = await alert_service.maybe_send_alert(txn2)
    assert fired2 is True
    assert len(webhook_dispatches) == 1
    url, payload = webhook_dispatches[0]
    assert url == "https://webhook.site/test-alert"
    assert payload["event"] == "budget_exceeded"
    assert payload["category"] == "groceries"
    assert payload["limit"] == 5000.0
    assert payload["spent"] == 6000.0
    assert payload["period"] == "2025-01"

    # 4. Transaction 3: 1000 KES (Total 7000 > 5000 limit) -> Idempotency: Does NOT fire again!
    txn3 = Transaction(
        account_id=account.id,
        amount=Decimal("1000.00"),
        category_id=category.id,
        merchant="Naivas",
        ref_code="TXN003",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.datetime(2025, 1, 20, 12, 0, 0, tzinfo=datetime.timezone.utc),
        raw_payload={},
    )
    db.add(txn3)
    await db.commit()

    fired3 = await alert_service.maybe_send_alert(txn3)
    assert fired3 is False
    # Still only 1 webhook dispatch recorded
    assert len(webhook_dispatches) == 1
