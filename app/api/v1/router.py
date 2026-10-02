"""Top-level API router for v1 endpoints."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, budgets, reports, transactions

api_router = APIRouter()

api_router.include_router(auth.router, tags=["Authentication"], prefix="/auth")
api_router.include_router(transactions.router, tags=["Transactions"], prefix="/transactions")
api_router.include_router(budgets.router, tags=["Budgets"], prefix="/budgets")
api_router.include_router(reports.router, tags=["Reports"], prefix="/reports")
api_router.include_router(admin.router, tags=["Admin"], prefix="/admin")
