"""Centralized V1 transaction-category definitions.

This module deliberately contains vocabulary only. Category persistence,
customization, and CRUD are deferred to a future category-domain sprint.
"""

from __future__ import annotations

EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Makan",
    "Transport",
    "Belanja",
    "Hiburan",
    "Kesehatan",
    "Tempat Tinggal",
    "Tagihan & Langganan",
    "Pendidikan",
    "Lainnya",
)

INCOME_CATEGORIES: tuple[str, ...] = (
    "Uang Saku",
    "Gaji",
    "Freelance",
    "Reimbursement",
    "Investasi",
    "Lainnya",
)

CATEGORIES_BY_TYPE: dict[str, tuple[str, ...]] = {
    "expense": EXPENSE_CATEGORIES,
    "income": INCOME_CATEGORIES,
}


def categories_for_type(transaction_type: str) -> tuple[str, ...]:
    """Return the standard categories for a transaction type.

    Args:
        transaction_type: ``income`` or ``expense``, case-insensitively.

    Returns:
        The immutable category vocabulary for the supplied transaction type.
    """

    return CATEGORIES_BY_TYPE.get(str(transaction_type).strip().lower(), ())


def is_standard_category(transaction_type: str, category: str) -> bool:
    """Return whether a category is part of the V1 vocabulary."""

    return str(category).strip() in categories_for_type(transaction_type)
