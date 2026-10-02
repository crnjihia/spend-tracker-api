"""Account repository for database operations."""

import uuid
from decimal import Decimal
from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType


class AccountRepository:
    """Repository handling persistence operations for financial accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, account_id: Union[str, uuid.UUID]) -> Optional[Account]:
        """Fetch account by ID."""
        try:
            uid = account_id if isinstance(account_id, uuid.UUID) else uuid.UUID(str(account_id))
        except (ValueError, TypeError):
            return None
        stmt = select(Account).where(Account.id == uid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_account_by_type(
        self, user_id: Union[str, uuid.UUID], account_type: AccountType
    ) -> Optional[Account]:
        """Fetch an account belonging to user by type."""
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        stmt = select(Account).where(
            Account.user_id == uid,
            Account.type == account_type,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_mpesa_account(
        self, user_id: Union[str, uuid.UUID], name: str = "M-Pesa Wallet"
    ) -> Account:
        """Get existing M-Pesa account for user or create one automatically."""
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        account = await self.get_user_account_by_type(uid, AccountType.MPESA)
        if not account:
            account = Account(
                user_id=uid,
                name=name,
                type=AccountType.MPESA,
                balance=Decimal("0.00"),
                currency="KES",
            )
            self.db.add(account)
            await self.db.flush()
        return account

    async def list_by_user(self, user_id: Union[str, uuid.UUID]) -> List[Account]:
        """List all accounts for a specific user."""
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        stmt = select(Account).where(Account.user_id == uid)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, account: Account) -> Account:
        """Persist a new account entity."""
        self.db.add(account)
        await self.db.flush()
        return account
