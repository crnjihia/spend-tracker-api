"""Report generation service for spending analytics and summaries."""

import datetime
import uuid
from collections import defaultdict
from typing import Any, Dict, Union

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionDirection


class ReportService:
    """Service producing analytical summaries and time-series spending reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(
        self,
        user_id: Union[str, uuid.UUID],
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> Dict[str, Any]:
        """Generate spending summary report across accounts for a user within a date range.

        Args:
            user_id: Target user UUID.
            from_date: Inclusive start date.
            to_date: Inclusive end date.

        Returns:
            Dict conforming to SummaryReport schema.
        """
        u_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))

        start_dt = datetime.datetime.combine(
            from_date, datetime.time.min, tzinfo=datetime.timezone.utc
        )
        end_dt = datetime.datetime.combine(to_date, datetime.time.max, tzinfo=datetime.timezone.utc)

        # 1. Fetch all outgoing transactions in date window
        stmt = (
            select(
                Transaction.category_id,
                Transaction.merchant,
                Transaction.amount,
                Transaction.occurred_at,
            )
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == u_id,
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                Transaction.direction == TransactionDirection.OUT,
            )
            .order_by(Transaction.occurred_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # Load all categories to map id -> slug
        cat_stmt = select(Category.id, Category.slug)
        cat_result = await self.db.execute(cat_stmt)
        cat_slug_map = {str(row[0]): row[1] for row in cat_result.all()}

        totals_by_category: Dict[str, float] = defaultdict(float)
        merchant_totals: Dict[str, float] = defaultdict(float)
        daily_series: Dict[str, float] = defaultdict(float)
        current_period_total = 0.0

        for cat_id, merchant, amount, occurred_at in rows:
            amount_float = float(amount)
            current_period_total += amount_float

            cat_slug = cat_slug_map.get(str(cat_id), "uncategorized") if cat_id else "uncategorized"
            totals_by_category[cat_slug] += amount_float

            if merchant:
                merchant_totals[merchant] += amount_float

            day_str = occurred_at.strftime("%Y-%m-%d")
            daily_series[day_str] += amount_float

        top_merchants = [
            {"merchant": m, "amount": round(a, 2)}
            for m, a in sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        daily_spend_series = [
            {"date": d, "amount": round(a, 2)}
            for d, a in sorted(daily_series.items(), key=lambda x: x[0])
        ]

        # 2. Compute Month-over-Month Delta
        # Prior month is from same day in previous month, or previous calendar month
        days_in_range = (to_date - from_date).days + 1
        prior_end_date = from_date - datetime.timedelta(days=1)
        prior_start_date = prior_end_date - datetime.timedelta(days=days_in_range - 1)

        prior_start_dt = datetime.datetime.combine(
            prior_start_date, datetime.time.min, tzinfo=datetime.timezone.utc
        )
        prior_end_dt = datetime.datetime.combine(
            prior_end_date, datetime.time.max, tzinfo=datetime.timezone.utc
        )

        prev_stmt = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == u_id,
                Transaction.occurred_at >= prior_start_dt,
                Transaction.occurred_at <= prior_end_dt,
                Transaction.direction == TransactionDirection.OUT,
            )
        )
        prev_result = await self.db.execute(prev_stmt)
        prior_total = float(prev_result.scalar_one())

        mom_delta = round(current_period_total - prior_total, 2)

        return {
            "from_date": from_date,
            "to_date": to_date,
            "totals_by_category": {k: round(v, 2) for k, v in totals_by_category.items()},
            "top_merchants": top_merchants,
            "month_over_month_delta": mom_delta,
            "daily_spend_series": daily_spend_series,
        }
