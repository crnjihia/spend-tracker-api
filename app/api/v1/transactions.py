"""Transactions API endpoints for M-Pesa ingestion and management."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection
from app.models.user import User
from app.repositories.account_repo import AccountRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.transaction import MpesaIngestionPayload, TransactionRead
from app.services.budget_alerts import BudgetAlertService
from app.services.categoriser import RuleBasedCategoriser

router = APIRouter()


@router.post(
    "/mpesa",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest M-Pesa transaction",
    description="Ingest, normalize, and auto-categorize an M-Pesa C2B or SMS confirmation payload. Reject duplicates.",
)
async def ingest_mpesa(
    payload: MpesaIngestionPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionRead:
    """Ingest and normalize an M-Pesa C2B or SMS transaction."""
    txn_repo = TransactionRepository(db)

    # 1. Idempotency Check: reject duplicate TransID
    existing = await txn_repo.get_by_ref_code(payload.TransID)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate transaction",
        )

    # 2. Retrieve or create user's M-Pesa account
    account_repo = AccountRepository(db)
    account = await account_repo.get_or_create_mpesa_account(user.id)

    # 3. Parse timestamp
    try:
        occurred_at = datetime.strptime(payload.TransTime, "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid TransTime format '{payload.TransTime}'. Expected YYYYMMDDHHMMSS",
        ) from exc

    try:
        amount_decimal = Decimal(str(payload.TransAmount))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid TransAmount '{payload.TransAmount}'",
        ) from exc

    # In personal finance spending tracking, C2B/Paybill/Till payments represent user outflows (expenses)
    direction = TransactionDirection.OUT
    merchant_name = (
        payload.BillRefNumber or payload.FirstName or f"Paybill {payload.BusinessShortCode}"
    )

    transaction = Transaction(
        account_id=account.id,
        amount=amount_decimal,
        merchant=merchant_name,
        ref_code=payload.TransID,
        occurred_at=occurred_at,
        direction=direction,
        raw_payload=payload.model_dump(),
        needs_review=False,
    )
    transaction.account = account

    # 4. Auto-categorize against system & user categories
    cat_stmt = select(Category)
    cat_res = await db.execute(cat_stmt)
    categories = list(cat_res.scalars().all())

    categoriser = RuleBasedCategoriser(categories)
    matched_category = await categoriser.categorise(transaction)
    if matched_category:
        transaction.category_id = matched_category.id
        transaction.category = matched_category
    else:
        # Ambiguous or no match
        transaction.category_id = None
        transaction.needs_review = True

    await txn_repo.create(transaction)

    # Update account balance (outflow deducts balance)
    account.balance = Decimal(str(account.balance)) - amount_decimal

    # 5. Check and dispatch budget alerts if exceeded
    alert_service = BudgetAlertService(db)
    await alert_service.maybe_send_alert(transaction)

    await db.commit()
    await db.refresh(transaction)

    return TransactionRead.model_validate(transaction)


@router.get(
    "",
    response_model=List[TransactionRead],
    summary="List transactions",
    description="Retrieve paginated list of transactions for the authenticated user.",
)
@router.get(
    "/",
    response_model=List[TransactionRead],
    include_in_schema=False,
)
async def list_transactions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[TransactionRead]:
    """List transactions for current user."""
    txn_repo = TransactionRepository(db)
    transactions = await txn_repo.list_by_user(user.id, limit=limit, offset=offset)
    return [TransactionRead.model_validate(t) for t in transactions]


@router.get(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Get transaction by ID",
    description="Retrieve a single transaction if owned by the authenticated user.",
)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionRead:
    """Get single transaction by ID."""
    txn_repo = TransactionRepository(db)
    transaction = await txn_repo.get_by_id(transaction_id, user_id=user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return TransactionRead.model_validate(transaction)
