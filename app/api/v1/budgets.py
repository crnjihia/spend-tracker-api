"""Budgets API routes for CRUD operations on user budgets."""

import uuid
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.budget import Budget
from app.models.category import Category
from app.models.user import User
from app.repositories.budget_repo import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate

router = APIRouter()


@router.post(
    "",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create category budget",
    description="Establish a monthly spending limit for a specific category and period (YYYY-MM).",
)
@router.post(
    "/",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_budget(
    payload: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetRead:
    """Create a new user budget."""
    repo = BudgetRepository(db)

    # Verify category exists
    try:
        cat_id = uuid.UUID(payload.category_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category_id '{payload.category_id}'",
        )

    category = await db.get(Category, cat_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{payload.category_id}' not found",
        )

    # Check duplicate budget for user/category/period
    existing = await repo.get_by_user_category_period(
        user_id=user.id,
        category_id=cat_id,
        period=payload.period,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A budget for category '{category.name}' and period '{payload.period}' already exists",
        )

    budget = Budget(
        user_id=user.id,
        category_id=cat_id,
        monthly_limit=Decimal(str(payload.monthly_limit)),
        alert_webhook_url=payload.alert_webhook_url,
        period=payload.period,
    )
    await repo.create(budget)
    await db.commit()
    await db.refresh(budget)

    return BudgetRead.model_validate(budget)


@router.get(
    "",
    response_model=List[BudgetRead],
    summary="List user budgets",
    description="Retrieve all budgets created by the authenticated user.",
)
@router.get(
    "/",
    response_model=List[BudgetRead],
    include_in_schema=False,
)
async def list_budgets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[BudgetRead]:
    """List all budgets for current user."""
    repo = BudgetRepository(db)
    budgets = await repo.list_by_user(user.id)
    return [BudgetRead.model_validate(b) for b in budgets]


@router.get(
    "/{budget_id}",
    response_model=BudgetRead,
    summary="Get budget by ID",
    description="Retrieve details of a single budget owned by the current user.",
)
async def get_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetRead:
    """Get single user budget."""
    repo = BudgetRepository(db)
    budget = await repo.get_by_id(budget_id, user_id=user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return BudgetRead.model_validate(budget)


@router.patch(
    "/{budget_id}",
    response_model=BudgetRead,
    summary="Update budget",
    description="Update monthly limit or alert webhook URL for a user budget.",
)
async def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BudgetRead:
    """Update a user budget."""
    repo = BudgetRepository(db)
    budget = await repo.get_by_id(budget_id, user_id=user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    await repo.update(
        budget,
        monthly_limit=payload.monthly_limit,
        alert_webhook_url=payload.alert_webhook_url,
    )
    await db.commit()
    await db.refresh(budget)

    return BudgetRead.model_validate(budget)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete budget",
    description="Delete a budget owned by the authenticated user.",
)
async def delete_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete a user budget."""
    repo = BudgetRepository(db)
    deleted = await repo.delete(budget_id, user_id=user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    await db.commit()
    return None
