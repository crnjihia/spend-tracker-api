"""Admin-only management endpoints protected by RBAC."""

from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterResponse

router = APIRouter()


@router.get(
    "/users",
    response_model=List[RegisterResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users",
    description="Administrative endpoint to view all registered users. Requires 'admin' role.",
)
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role("admin")),
) -> List[RegisterResponse]:
    """List all registered users (Admin only)."""
    repo = UserRepository(db)
    users = await repo.get_all(limit=limit, offset=offset)
    return [
        RegisterResponse(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]
