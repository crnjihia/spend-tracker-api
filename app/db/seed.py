"""Database seeding utilities for system categories and initial configuration."""

import asyncio
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.category import Category

DEFAULT_CATEGORIES: List[Dict[str, Any]] = [
    {
        "name": "Groceries",
        "slug": "groceries",
        "is_system": True,
        "keywords": [
            "supermarket",
            "grocery",
            "market",
            "naivas",
            "carrefour",
            "quickmart",
            "foodplus",
        ],
    },
    {
        "name": "Utilities",
        "slug": "utilities",
        "is_system": True,
        "keywords": [
            "kplc",
            "electricity",
            "water",
            "nairobi water",
            "token",
            "utility",
            "kenya power",
        ],
    },
    {
        "name": "SACCO",
        "slug": "sacco",
        "is_system": True,
        "keywords": ["sacco", "harambee", "stima", "chuna", "shares", "deposit", "sacco001"],
    },
    {
        "name": "M-Pesa",
        "slug": "mpesa",
        "is_system": True,
        "keywords": ["mpesa fee", "safaricom", "send money", "agent withdrawal", "mpesa charges"],
    },
    {
        "name": "Transport",
        "slug": "transport",
        "is_system": True,
        "keywords": ["fuel", "total", "shell", "rubis", "uber", "bolt", "matatu"],
    },
    {
        "name": "Entertainment",
        "slug": "entertainment",
        "is_system": True,
        "keywords": ["netflix", "spotify", "cinema", "restaurant", "cafe", "bar"],
    },
]


async def seed_categories(session: AsyncSession) -> None:
    """Insert default system categories if they do not already exist.

    Args:
        session: Active asynchronous SQLAlchemy session.
    """
    for cat_data in DEFAULT_CATEGORIES:
        stmt = select(Category).where(Category.slug == cat_data["slug"])
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            continue
        category = Category(**cat_data)
        session.add(category)
    await session.commit()


async def _run_seed() -> None:
    async with async_session() as session:
        await seed_categories(session)


def run_seed() -> None:
    """Run seeding synchronously (e.g. CLI or migration post-hook)."""
    asyncio.run(_run_seed())


if __name__ == "__main__":
    run_seed()
