"""Authentication business logic service."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.repositories.account_repo import AccountRepository
from app.repositories.user_repo import UserRepository


class AuthService:
    """Service handling user registration, authentication, token rotation, and revocation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.account_repo = AccountRepository(db)

    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Register a new user and initialize a default M-Pesa account.

        Args:
            email: Unique email address.
            password: Plaintext password (min 8 chars).
            full_name: Optional user display name.
            role: UserRole enum value.

        Returns:
            User: Newly registered User entity.

        Raises:
            ValueError: If user with email already exists.
        """
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("User with this email already exists")

        user = User.create(email=email, password=password, full_name=full_name, role=role)
        await self.user_repo.create(user)

        # Create default M-Pesa account for seamless transaction ingestion
        await self.account_repo.get_or_create_mpesa_account(user.id, name="Default M-Pesa")

        await self.db.commit()
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password.

        Args:
            email: User's email.
            password: User's password.

        Returns:
            User if valid, None otherwise.
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens and store the hashed refresh token.

        Args:
            user: User entity for whom tokens are issued.

        Returns:
            Dict containing access_token, refresh_token, and token_type.
        """
        user_id_str = str(user.id)
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        access_token = create_access_token(
            subject=user_id_str,
            extra_claims={"role": user_role_str, "email": user.email},
        )
        raw_refresh = create_refresh_token(subject=user_id_str)

        # Deterministic SHA-256 hash for fast, unique lookup
        token_hash = hash_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        self.db.add(refresh_token)
        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
        }

    async def rotate_refresh_token(self, raw_token: str) -> Dict[str, str]:
        """Rotate a refresh token by revoking the old one and issuing a fresh pair.

        Args:
            raw_token: Unhashed JWT refresh token presented by client.

        Returns:
            Dict containing new token pair.

        Raises:
            ValueError: If token is invalid, expired, revoked, or user not found.
        """
        try:
            payload = jwt.decode(
                raw_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            token_type = payload.get("type")
            if token_type and token_type != "refresh":
                raise ValueError("Provided token is not a refresh token")
        except JWTError as exc:
            raise ValueError("Invalid refresh token") from exc

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Invalid token payload: missing subject")

        token_hash = hash_token(raw_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        token_obj: Optional[RefreshToken] = result.scalar_one_or_none()

        if not token_obj:
            raise ValueError("Refresh token not found or already revoked")

        now = datetime.now(timezone.utc)
        # Check expiry
        if token_obj.expires_at.tzinfo is None:
            token_expires = token_obj.expires_at.replace(tzinfo=timezone.utc)
        else:
            token_expires = token_obj.expires_at

        if token_expires < now:
            token_obj.revoked = True
            await self.db.commit()
            raise ValueError("Refresh token has expired")

        # Revoke the used token (one-time use rotation guarantee)
        token_obj.revoked = True
        await self.db.flush()

        user = await self.user_repo.get_by_id(user_id_str)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        tokens = await self.generate_tokens(user)
        return tokens

    async def revoke_refresh_token(self, raw_token: str) -> None:
        """Revoke a refresh token on logout.

        Args:
            raw_token: Unhashed JWT refresh token.
        """
        token_hash = hash_token(raw_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        token_obj: Optional[RefreshToken] = result.scalar_one_or_none()
        if token_obj:
            token_obj.revoked = True
            await self.db.commit()
