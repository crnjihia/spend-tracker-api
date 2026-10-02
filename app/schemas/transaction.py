"""Transaction schemas for M-Pesa ingestion and API responses."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MpesaIngestionPayload(BaseModel):
    """Raw M-Pesa C2B or SMS-parsed callback payload."""

    TransID: str = Field(
        ..., description="Unique M-Pesa transaction reference code", examples=["QGH7XYZ123"]
    )
    TransAmount: str = Field(..., description="Transaction amount as string", examples=["1500.00"])
    BusinessShortCode: str = Field(..., description="Paybill or Till Number", examples=["247247"])
    BillRefNumber: str = Field(
        ..., description="Account or reference number", examples=["SACCO001"]
    )
    MSISDN: str = Field(
        ..., description="Customer mobile number in MSISDN format", examples=["254712345678"]
    )
    TransTime: str = Field(
        ..., description="Timestamp in YYYYMMDDHHMMSS format", examples=["20250115143022"]
    )
    FirstName: str = Field(..., description="Sender or receiver name", examples=["John"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "TransID": "QGH7XYZ123",
                "TransAmount": "1500.00",
                "BusinessShortCode": "247247",
                "BillRefNumber": "SACCO001",
                "MSISDN": "254712345678",
                "TransTime": "20250115143022",
                "FirstName": "John",
            }
        }
    )


class TransactionCreate(BaseModel):
    """Payload to create a generic transaction."""

    account_id: str = Field(..., description="ID of associated user account")
    amount: float = Field(..., gt=0, description="Transaction amount")
    merchant: Optional[str] = Field(None, description="Merchant or party name")
    direction: str = Field(
        ..., pattern="^(in|out)$", description="Money flow direction (in or out)"
    )
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Raw ingestion payload")


class TransactionRead(BaseModel):
    """Serialized transaction response representation."""

    id: str
    account_id: str
    amount: float
    category_id: Optional[str] = None
    merchant: Optional[str] = None
    ref_code: str
    occurred_at: datetime
    direction: str
    raw_payload: Dict[str, Any]
    created_at: datetime
    needs_review: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "account_id", mode="before")
    @classmethod
    def serialize_uuid(cls, v: Any) -> str:
        return str(v) if v is not None else ""

    @field_validator("category_id", mode="before")
    @classmethod
    def serialize_opt_uuid(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

    @field_validator("direction", mode="before")
    @classmethod
    def serialize_direction(cls, v: Any) -> str:
        return v.value if hasattr(v, "value") else str(v)

    @field_validator("amount", mode="before")
    @classmethod
    def serialize_amount(cls, v: Any) -> float:
        return float(v) if v is not None else 0.0
