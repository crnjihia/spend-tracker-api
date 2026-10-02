"""Budget schemas for creation, updating, and serialization."""

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetCreate(BaseModel):
    """Payload to establish a category budget for a monthly period."""

    category_id: str = Field(..., description="Target category UUID")
    monthly_limit: float = Field(
        ..., gt=0, description="Spending limit for the period", examples=[10000.0]
    )
    alert_webhook_url: Optional[str] = Field(
        None,
        description="Webhook URL triggered when budget exceeded",
        examples=["https://webhook.site/alert"],
    )
    period: str = Field(..., description="Budget period in YYYY-MM format", examples=["2025-01"])

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        """Validate period matches YYYY-MM."""
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("period must be in YYYY-MM format (e.g. 2025-01)")
        return v


class BudgetUpdate(BaseModel):
    """Payload to update an existing budget."""

    monthly_limit: Optional[float] = Field(None, gt=0, description="New spending limit")
    alert_webhook_url: Optional[str] = Field(None, description="New webhook URL")


class BudgetRead(BaseModel):
    """Serialized budget representation."""

    id: str
    user_id: str
    category_id: str
    monthly_limit: float
    alert_webhook_url: Optional[str] = None
    period: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", "category_id", mode="before")
    @classmethod
    def serialize_uuid(cls, v: Any) -> str:
        return str(v) if v is not None else ""

    @field_validator("monthly_limit", mode="before")
    @classmethod
    def serialize_limit(cls, v: Any) -> float:
        return float(v) if v is not None else 0.0
