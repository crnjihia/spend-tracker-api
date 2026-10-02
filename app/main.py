"""FastAPI Application entry point for Matumizi API."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.session import async_engine

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to verify database connectivity on startup."""
    logger.info("Initializing Matumizi API...", project=settings.PROJECT_NAME)
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity established successfully")
    except Exception as exc:
        logger.warning("Could not verify database connection on startup", error=str(exc))
    yield
    logger.info("Shutting down Matumizi API...")
    await async_engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Matumizi API",
        description=(
            "Personal finance tracking REST API built for Kenyan spending habits. "
            "Handles M-Pesa transactions, SACCO contributions, utility bills, and budgets."
        ),
        version="0.1.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Attach rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and structured logging middleware
    @app.middleware("http")
    async def request_id_and_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.id = req_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id, path=request.url.path)

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # Register custom exception handlers
    register_exception_handlers(app)

    # Include API router under /api/v1 and alias root
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_router)

    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        description="Root endpoint providing service details and documentation links.",
    )
    async def root() -> dict:
        """Root welcome endpoint with navigation links."""
        return {
            "name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "documentation": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "message": "Welcome to Matumizi API. Visit /docs for interactive Swagger UI.",
        }

    @app.get(
        "/health",
        tags=["Health"],
        summary="Service health check",
        description="Verify service availability and database connectivity.",
    )
    async def health_check() -> JSONResponse:
        """Health check endpoint confirming database reachability."""
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"status": "ok", "database": "connected"}
            )
        except Exception as exc:
            logger.error("Health check failed", error=str(exc))
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "database": "unreachable", "error": str(exc)},
            )

    return app


app = create_app()
