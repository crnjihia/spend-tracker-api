"""Custom domain exceptions and FastAPI exception handlers."""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse


class MatumiziException(Exception):
    """Base exception for Matumizi API domain errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EntityNotFoundException(MatumiziException):
    """Raised when an entity is not found in database."""

    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateEntityException(MatumiziException):
    """Raised when a unique constraint or idempotency check fails."""

    def __init__(self, message: str = "Duplicate resource detected"):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class InsufficientPermissionsException(MatumiziException):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class AuthenticationException(MatumiziException):
    """Raised when credentials or authentication fails."""

    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

unauthorized_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="User is inactive or does not exist",
    headers={"WWW-Authenticate": "Bearer"},
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application instance."""

    @app.exception_handler(MatumiziException)
    async def matumizi_exception_handler(request: Request, exc: MatumiziException) -> JSONResponse:
        request_id = getattr(request.state, "id", None)
        content: Dict[str, Any] = {"detail": exc.message}
        if request_id:
            content["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=content)
