"""Transaction repository for database operations."""

import calendar
import datetime
import uuid
from typing import List, Optional, Union

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.transaction import Transaction, TransactionDirection


class TransactionRepository:
    """Repository handling persistence operations for Transaction entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_ref_code(self, ref_code: str) -> Optional[Transaction]:
        """Fetch transaction by unique M-Pesa / external reference code."""
        stmt = (
            select(Transaction)
            .where(Transaction.ref_code == ref_code)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, transaction_id: Union[str, uuid.UUID], user_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Optional[Transaction]:
        """Fetch transaction by ID, optionally verifying account ownership by user."""
        try:
            t_id = (
                transaction_id
                if isinstance(transaction_id, uuid.UUID)
                else uuid.UUID(str(transaction_id))
            )
        except (ValueError, TypeError):
            return None

        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Transaction.id == t_id)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
        )
        if user_id is not None:
            u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            stmt = stmt.where(Account.user_id == u_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction entity."""
        self.db.add(transaction)
        await self.db.flush()
        return transaction

    async def sum_by_category_month(
        self,
        user_id: Union[str, uuid.UUID],
        category_id: Union[str, uuid.UUID],
        period: str,  # "YYYY-MM"
    ) -> float:
        """Calculate total month-to-date outflow for a user and category."""
        u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        c_id = category_id if isinstance(category_id, uuid.UUID) else uuid.UUID(str(category_id))

        year, month = map(int, period.split("-"))
        _, last_day = calendar.monthrange(year, month)
        start_dt = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        end_dt = datetime.datetime(
            year, month, last_day, 23, 59, 59, 999999, tzinfo=datetime.timezone.utc
        )

        stmt = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == u_id,
                Transaction.category_id == c_id,
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                Transaction.direction == TransactionDirection.OUT,
            )
        )
        result = await self.db.execute(stmt)
        total = result.scalar_one()
        return float(total)

    async def list_by_user_and_date_range(
        self,
        user_id: Union[str, uuid.UUID],
        from_dt: datetime.datetime,
        to_dt: datetime.datetime,
    ) -> List[Transaction]:
        """Fetch all transactions for a user within a datetime range."""
        u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == u_id,
                Transaction.occurred_at >= from_dt,
                Transaction.occurred_at <= to_dt,
            )
            .order_by(Transaction.occurred_at.asc())
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: Union[str, uuid.UUID],
        limit: int = 50,
        offset: int = 0,
    ) -> List[Transaction]:
        """Fetch paginated transactions for a user."""
        u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == u_id)
            .order_by(Transaction.occurred_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Transaction.account), selectinload(Transaction.category))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
