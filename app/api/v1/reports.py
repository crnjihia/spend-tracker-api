"""Reports API routes for financial aggregations and spend analytics."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.report import SummaryReport
from app.services.reports import ReportService

router = APIRouter()


@router.get(
    "/summary",
    response_model=SummaryReport,
    summary="Get spend summary report",
    description="Compute category totals, top 10 merchants, month-over-month spend delta, and daily spend series.",
)
async def get_summary(
    from_date: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (YYYY-MM-DD)",
        examples=["2025-01-01"],
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to",
        description="End date (YYYY-MM-DD)",
        examples=["2025-01-31"],
    ),
    from_date_alt: Optional[date] = Query(
        None,
        alias="from_date",
        description="Alternative parameter name for start date",
        include_in_schema=False,
    ),
    to_date_alt: Optional[date] = Query(
        None,
        alias="to_date",
        description="Alternative parameter name for end date",
        include_in_schema=False,
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SummaryReport:
    """Generate financial spend summary report for the user within date range."""
    effective_from = from_date or from_date_alt
    effective_to = to_date or to_date_alt

    if not effective_from or not effective_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'from' and 'to' date parameters are required in YYYY-MM-DD format",
        )

    if effective_from > effective_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'from' date must be before or equal to 'to' date",
        )

    service = ReportService(db)
    data = await service.summary(user.id, effective_from, effective_to)
    return SummaryReport(**data)
