"""Financial report schemas."""

from datetime import date
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MerchantSpend(BaseModel):
    """Spend aggregation per merchant."""

    merchant: str
    amount: float


class DailySpend(BaseModel):
    """Daily spend aggregation."""

    date: str
    amount: float


class SummaryReport(BaseModel):
    """Comprehensive spending summary report for a user."""

    from_date: date = Field(..., description="Start of reporting window")
    to_date: date = Field(..., description="End of reporting window")
    totals_by_category: Dict[str, float] = Field(
        default_factory=dict,
        description="Aggregated spend per category slug",
        examples=[{"groceries": 12500.0, "utilities": 3200.0}],
    )
    top_merchants: List[MerchantSpend] = Field(
        default_factory=list,
        description="Top 10 merchants by spend",
        examples=[[{"merchant": "Naivas Supermarket", "amount": 8500.0}]],
    )
    month_over_month_delta: float = Field(
        ...,
        description="Difference in spend compared to previous month period",
        examples=[1250.0],
    )
    daily_spend_series: List[DailySpend] = Field(
        default_factory=list,
        description="Daily spending time series",
        examples=[[{"date": "2025-01-15", "amount": 1500.0}]],
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def check_dates(self) -> "SummaryReport":
        """Verify from_date is before or equal to to_date."""
        if self.from_date > self.to_date:
            raise ValueError("to_date must be greater than or equal to from_date")
        return self
