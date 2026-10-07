"""FastAPI dependency injection providers."""

from typing import Annotated, AsyncGenerator, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import credentials_exception, unauthorized_exception
from app.db.session import async_session
from app.models.user import User
from app.repositories.user_repo import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session from the session pool and ensure proper closing.

    Yields:
        AsyncSession: Active asynchronous database session.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT access token and return the authenticated user record.

    Args:
        credentials: Bearer HTTP credentials parsed from Authorization header.
        db: Database session.

    Returns:
        User: Active authenticated user instance.

    Raises:
        HTTPException: If token is invalid, expired, or user not found/inactive.
    """
    if credentials is None or not credentials.credentials:
        raise credentials_exception

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise credentials_exception

        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id_str)
    if user is None or not user.is_active:
        raise unauthorized_exception
    return user


def require_role(required_role: str) -> Callable:
    """Dependency factory checking that the authenticated user possesses the required role.

    Args:
        required_role: Required user role string (e.g. 'admin').

    Returns:
        Callable: Dependency returning the user if role matches, raising 403 otherwise.
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role_str != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker
