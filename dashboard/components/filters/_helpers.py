"""Shared UI-state helpers for page-local filters."""

from __future__ import annotations

import streamlit as st

from services.category_definitions import categories_for_type

TRANSACTION_TYPE_OPTIONS = ("All", "Income", "Expense")


def category_options_for_type(
    categories: list[str],
    transaction_type: str,
) -> list[str]:
    """Return valid Category options for the selected transaction type."""

    normalized_type = str(transaction_type).strip().lower()
    if normalized_type in {"income", "expense"}:
        return list(categories_for_type(normalized_type))

    return [category for category in categories if category != "All"]


def initialize_local_filter_state(
    category_key: str,
    transaction_type_key: str,
    categories: list[str],
) -> None:
    """Initialize valid values for one page's local filter state."""

    if st.session_state.get(category_key) not in categories:
        st.session_state[category_key] = "All"
    if st.session_state.get(transaction_type_key) not in (
        TRANSACTION_TYPE_OPTIONS
    ):
        st.session_state[transaction_type_key] = "All"
