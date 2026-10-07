"""Budget exceed alert service with idempotent webhook dispatching."""

from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.redis import get_redis
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection
from app.repositories.budget_repo import BudgetRepository
from app.repositories.transaction_repo import TransactionRepository

logger = get_logger(__name__)


class BudgetAlertService:
    """Handles budget exceed alerts with idempotency guaranteed via Redis."""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.budget_repo = BudgetRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self._redis = redis_client

    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def maybe_send_alert(self, transaction: Transaction) -> bool:
        """Check if a new outflow transaction pushes category spend beyond budget and fires webhook once.

        Args:
            transaction: Newly recorded transaction.

        Returns:
            bool: True if alert webhook was dispatched, False otherwise.
        """
        # Alerts only apply to expense/outflow transactions that are categorized
        direction_val = (
            transaction.direction.value
            if hasattr(transaction.direction, "value")
            else str(transaction.direction)
        )
        if direction_val != TransactionDirection.OUT.value or not transaction.category_id:
            return False

        # Ensure account is loaded to access user_id
        if not transaction.account:
            account = await self.db.get(Account, transaction.account_id)
            if not account:
                return False
            user_id = str(account.user_id)
        else:
            user_id = str(transaction.account.user_id)

        period = transaction.occurred_at.strftime("%Y-%m")

        # Query budget for this user, category, and period
        budget: Optional[Budget] = await self.budget_repo.get_by_user_category_period(
            user_id=user_id,
            category_id=str(transaction.category_id),
            period=period,
        )
        if not budget or not budget.alert_webhook_url:
            return False

        # Calculate month-to-date total outflow for this category
        total_spent = await self.transaction_repo.sum_by_category_month(
            user_id=user_id,
            category_id=str(transaction.category_id),
            period=period,
        )

        monthly_limit = float(budget.monthly_limit)
        if total_spent <= monthly_limit:
            return False

        # Check idempotency in Redis: alert must only fire ONCE per period
        redis_key = f"budget_alert:{budget.user_id}:{budget.category_id}:{period}"
        try:
            already_alerted = await self.redis.get(redis_key)
            if already_alerted:
                logger.info("Budget alert already triggered for period", key=redis_key)
                return False
        except Exception as exc:
            logger.warning("Redis check failed, falling back", error=str(exc))

        # Retrieve category slug
        cat_slug = "uncategorized"
        if budget.category:
            cat_slug = budget.category.slug
        else:
            cat_obj = await self.db.get(Category, budget.category_id)
            if cat_obj:
                cat_slug = cat_obj.slug

        payload = {
            "event": "budget_exceeded",
            "category": cat_slug,
            "limit": monthly_limit,
            "spent": total_spent,
            "period": period,
        }

        # Dispatch webhook
        dispatched = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(budget.alert_webhook_url, json=payload)
                logger.info(
                    "Budget alert webhook sent",
                    url=budget.alert_webhook_url,
                    status=resp.status_code,
                    spent=total_spent,
                )
                dispatched = True
        except Exception as exc:
            logger.error(
                "Failed to dispatch budget alert webhook",
                error=str(exc),
                url=budget.alert_webhook_url,
            )

        # Mark in Redis only after a successful dispatch so a failed webhook can retry
        if dispatched:
            try:
                await self.redis.set(redis_key, "1", ex=60 * 86400)
            except Exception as exc:
                logger.warning("Failed to set Redis alert flag", error=str(exc))

        return dispatched
