"""Transaction domain model."""

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class TransactionDirection(str, enum.Enum):
    """Direction of money flow for a transaction."""

    IN = "in"
    OUT = "out"


class Transaction(Base):
    """Financial transaction record."""

    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("ref_code", name="uq_transaction_ref_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("categories.id"), nullable=True, index=True
    )
    merchant: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ref_code: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(
        Enum(TransactionDirection, name="transaction_direction", native_enum=False),
        nullable=False,
    )
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account", back_populates="transactions", lazy="selectin"
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="transactions", lazy="selectin"
    )
