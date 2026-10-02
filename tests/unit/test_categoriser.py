"""Unit tests for the categorisation engine."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection
from app.services.categoriser import RuleBasedCategoriser


@pytest.mark.asyncio
async def test_rule_based_categoriser_single_match():
    """Test successful category match when keyword aligns unambiguously."""
    cat_food = Category(
        id=uuid.uuid4(),
        name="Groceries",
        slug="groceries",
        is_system=True,
        keywords=["grocery", "supermarket", "naivas", "carrefour"],
    )
    cat_utility = Category(
        id=uuid.uuid4(),
        name="Utilities",
        slug="utilities",
        is_system=True,
        keywords=["kplc", "electricity", "water", "token"],
    )
    categoriser = RuleBasedCategoriser([cat_food, cat_utility])

    txn = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        amount=Decimal("2500.00"),
        merchant="Naivas Supermarket Junction",
        ref_code="NV12345",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.now(timezone.utc),
        raw_payload={"BillRefNumber": "STORE01"},
    )
    result = await categoriser.categorise(txn)
    assert result is not None
    assert result.slug == "groceries"


@pytest.mark.asyncio
async def test_rule_based_categoriser_bill_ref_match():
    """Test matching based on BillRefNumber in raw payload."""
    cat_sacco = Category(
        id=uuid.uuid4(),
        name="SACCO",
        slug="sacco",
        is_system=True,
        keywords=["sacco", "harambee", "stima", "shares"],
    )
    categoriser = RuleBasedCategoriser([cat_sacco])

    txn = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        amount=Decimal("5000.00"),
        merchant="Paybill 247247",
        ref_code="SACCO987",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.now(timezone.utc),
        raw_payload={"BillRefNumber": "STIMA_SHARES_01"},
    )
    result = await categoriser.categorise(txn)
    assert result is not None
    assert result.slug == "sacco"


@pytest.mark.asyncio
async def test_rule_based_categoriser_ambiguity_returns_none():
    """Test that ambiguous keyword matches return None so transaction can be flagged for review."""
    cat_a = Category(
        id=uuid.uuid4(),
        name="Market",
        slug="market",
        is_system=True,
        keywords=["quick", "express"],
    )
    cat_b = Category(
        id=uuid.uuid4(),
        name="Transport",
        slug="transport",
        is_system=True,
        keywords=["express", "shuttle"],
    )
    categoriser = RuleBasedCategoriser([cat_a, cat_b])

    # Both categories match the word 'express'
    txn = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        amount=Decimal("500.00"),
        merchant="Express Delivery",
        ref_code="EXP001",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.now(timezone.utc),
        raw_payload={},
    )
    result = await categoriser.categorise(txn)
    assert result is None


@pytest.mark.asyncio
async def test_rule_based_categoriser_no_match():
    """Test that unknown merchants return None."""
    cat_food = Category(
        id=uuid.uuid4(),
        name="Groceries",
        slug="groceries",
        is_system=True,
        keywords=["naivas", "carrefour"],
    )
    categoriser = RuleBasedCategoriser([cat_food])

    txn = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        amount=Decimal("100.00"),
        merchant="Unrecognized Vendor XYZ",
        ref_code="XYZ123",
        direction=TransactionDirection.OUT,
        occurred_at=datetime.now(timezone.utc),
        raw_payload={},
    )
    result = await categoriser.categorise(txn)
    assert result is None
