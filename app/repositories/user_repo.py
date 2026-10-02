"""User repository for database operations."""

import uuid
from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository handling persistence operations for User entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by unique email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[User]:
        """Fetch a user by primary key ID."""
        try:
            uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return None
        stmt = select(User).where(User.id == uid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Fetch all users with pagination (admin only)."""
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        """Persist a new user entity."""
        self.db.add(user)
        await self.db.flush()
        return user
