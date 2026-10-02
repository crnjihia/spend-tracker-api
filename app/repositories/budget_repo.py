"""Budget repository for database operations."""

import uuid
from decimal import Decimal
from typing import List, Optional, Union

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget


class BudgetRepository:
    """Repository handling persistence operations for Budget entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, budget_id: Union[str, uuid.UUID], user_id: Optional[Union[str, uuid.UUID]] = None
    ) -> Optional[Budget]:
        """Fetch a budget by ID, optionally ensuring ownership by user_id."""
        try:
            b_id = budget_id if isinstance(budget_id, uuid.UUID) else uuid.UUID(str(budget_id))
        except (ValueError, TypeError):
            return None

        stmt = select(Budget).where(Budget.id == b_id)
        if user_id is not None:
            u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            stmt = stmt.where(Budget.user_id == u_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_category_period(
        self,
        user_id: Union[str, uuid.UUID],
        category_id: Union[str, uuid.UUID],
        period: str,
    ) -> Optional[Budget]:
        """Fetch budget matching user, category, and period (YYYY-MM)."""
        try:
            u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            c_id = (
                category_id if isinstance(category_id, uuid.UUID) else uuid.UUID(str(category_id))
            )
        except (ValueError, TypeError):
            return None

        stmt = select(Budget).where(
            and_(
                Budget.user_id == u_id,
                Budget.category_id == c_id,
                Budget.period == period,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, budget: Budget) -> Budget:
        """Persist a new budget entity."""
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def list_by_user(self, user_id: Union[str, uuid.UUID]) -> List[Budget]:
        """List all budgets belonging to a specific user."""
        u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        stmt = select(Budget).where(Budget.user_id == u_id).order_by(Budget.period.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        budget: Budget,
        monthly_limit: Optional[float] = None,
        alert_webhook_url: Optional[str] = None,
    ) -> Budget:
        """Update existing budget properties."""
        if monthly_limit is not None:
            budget.monthly_limit = Decimal(str(monthly_limit))
        if alert_webhook_url is not None:
            budget.alert_webhook_url = alert_webhook_url
        await self.db.flush()
        return budget

    async def delete(
        self, budget_id: Union[str, uuid.UUID], user_id: Union[str, uuid.UUID]
    ) -> bool:
        """Delete a budget owned by the specified user. Returns True if deleted."""
        budget = await self.get_by_id(budget_id, user_id=user_id)
        if not budget:
            return False
        await self.db.delete(budget)
        await self.db.flush()
        return True
