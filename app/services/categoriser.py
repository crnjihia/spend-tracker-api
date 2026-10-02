"""Categorisation engine protocol and rule-based keyword matcher."""

import re
from typing import List, Optional, Protocol, runtime_checkable

from app.models.category import Category
from app.models.transaction import Transaction


@runtime_checkable
class CategoriserProtocol(Protocol):
    """Categoriser protocol allowing interchangeable classification backends (rules, LLMs, ML)."""

    async def categorise(self, transaction: Transaction) -> Optional[Category]:
        """Categorise a transaction based on its metadata.

        Args:
            transaction: The transaction entity to classify.

        Returns:
            Category if a single unambiguous match is found, None if ambiguous or no match.
        """
        ...


class RuleBasedCategoriser:
    """Rule-based categoriser matching keywords against merchant, reference, and payload."""

    def __init__(self, categories: List[Category]):
        """Initialize with available system/user categories.

        Args:
            categories: List of categories with associated keywords.
        """
        self.categories = categories

    async def categorise(self, transaction: Transaction) -> Optional[Category]:
        """Match transaction against category keywords.

        Args:
            transaction: Transaction instance.

        Returns:
            Category or None.
        """
        # Collect search text from all relevant fields
        search_targets = [
            transaction.merchant or "",
            transaction.ref_code or "",
        ]

        if isinstance(transaction.raw_payload, dict):
            for key in ["BillRefNumber", "BusinessShortCode", "FirstName"]:
                val = transaction.raw_payload.get(key)
                if val:
                    search_targets.append(str(val))

        combined_text = " ".join(search_targets).lower()
        matching_categories: List[Category] = []

        for category in self.categories:
            keywords = category.keywords or []
            if isinstance(keywords, list):
                for kw in keywords:
                    if not kw:
                        continue
                    # Match as word boundary or direct substring
                    pattern = rf"\b{re.escape(str(kw).lower())}\b"
                    if re.search(pattern, combined_text) or str(kw).lower() in combined_text:
                        matching_categories.append(category)
                        break

        # Ambiguous if multiple categories match; None if none match
        if len(matching_categories) == 1:
            return matching_categories[0]

        return None
