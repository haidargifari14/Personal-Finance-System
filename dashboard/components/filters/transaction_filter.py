"""Local operational filters for the Transactions workspace."""

from __future__ import annotations

from typing import TypedDict

import streamlit as st

from dashboard.components.filters._helpers import TRANSACTION_TYPE_OPTIONS

SORT_BY_OPTIONS = ("Date", "Amount", "Category")
SORT_ORDER_OPTIONS = ("Descending", "Ascending")
TRANSACTION_SEARCH_KEY = "transaction_search"
TRANSACTION_CATEGORY_KEY = "transaction_category"
TRANSACTION_TYPE_KEY = "transaction_transaction_type"
TRANSACTION_MIN_AMOUNT_KEY = "transaction_min_amount"
TRANSACTION_MAX_AMOUNT_KEY = "transaction_max_amount"
TRANSACTION_SORT_BY_KEY = "transaction_sort_by"
TRANSACTION_SORT_ORDER_KEY = "transaction_sort_order"
TRANSACTION_FILTER_DEFAULTS = {
    TRANSACTION_SEARCH_KEY: "",
    TRANSACTION_CATEGORY_KEY: "All",
    TRANSACTION_TYPE_KEY: "All",
    TRANSACTION_MIN_AMOUNT_KEY: None,
    TRANSACTION_MAX_AMOUNT_KEY: None,
    TRANSACTION_SORT_BY_KEY: "Date",
    TRANSACTION_SORT_ORDER_KEY: "Descending",
}


class TransactionFilterValues(TypedDict):
    """Values selected in the Transactions local filter."""

    search: str
    category: str
    transaction_type: str
    minimum_amount: int | None
    maximum_amount: int | None
    sort_by: str
    sort_order: str


def render_transaction_filter(
    categories: list[str],
    search: str,
) -> TransactionFilterValues:
    """Render the Transactions advanced filter and return selected values."""

    available_categories = categories or ["All"]
    _initialize_transaction_filter_state(available_categories)

    with st.container(border=False, key="transactions-filters"):
        title_column, reset_column = st.columns([5, 1])
        with title_column:
            st.markdown(
                "<div class=\"pf-transactions-section-title\">"
                "<span class=\"material-symbols-rounded\">filter_alt</span>"
                "Advanced filters</div>",
                unsafe_allow_html=True,
            )
        with reset_column:
            st.button(
                "Reset filters",
                icon=":material/filter_alt_off:",
                on_click=reset_transaction_filters,
                key="transactions_reset_filters",
                width="stretch",
            )

        category_column, type_column, minimum_column, maximum_column = st.columns(4)
        with category_column:
            category = st.selectbox(
                "Category",
                options=available_categories,
                key=TRANSACTION_CATEGORY_KEY,
                persist_state="session",
            )
        with type_column:
            transaction_type = st.selectbox(
                "Transaction type",
                options=TRANSACTION_TYPE_OPTIONS,
                key=TRANSACTION_TYPE_KEY,
                persist_state="session",
            )
        with minimum_column:
            minimum_amount = st.number_input(
                "Minimum amount",
                min_value=0,
                value=None,
                placeholder="No minimum",
                step=1000,
                key=TRANSACTION_MIN_AMOUNT_KEY,
                persist_state="session",
            )
        with maximum_column:
            maximum_amount = st.number_input(
                "Maximum amount",
                min_value=0,
                value=None,
                placeholder="No maximum",
                step=1000,
                key=TRANSACTION_MAX_AMOUNT_KEY,
                persist_state="session",
            )

        sort_column, order_column, _ = st.columns([1, 1, 2])
        with sort_column:
            sort_by = st.selectbox(
                "Sort by",
                options=SORT_BY_OPTIONS,
                key=TRANSACTION_SORT_BY_KEY,
                persist_state="session",
            )
        with order_column:
            sort_order = st.selectbox(
                "Order",
                options=SORT_ORDER_OPTIONS,
                key=TRANSACTION_SORT_ORDER_KEY,
                persist_state="session",
            )

    return {
        "search": search,
        "category": category,
        "transaction_type": transaction_type,
        "minimum_amount": minimum_amount,
        "maximum_amount": maximum_amount,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


def _initialize_transaction_filter_state(categories: list[str]) -> None:
    """Initialize Transactions-only filter state before rendering widgets."""

    for key, value in TRANSACTION_FILTER_DEFAULTS.items():
        st.session_state.setdefault(key, value)

    if st.session_state[TRANSACTION_CATEGORY_KEY] not in categories:
        st.session_state[TRANSACTION_CATEGORY_KEY] = "All"
    if st.session_state[TRANSACTION_TYPE_KEY] not in TRANSACTION_TYPE_OPTIONS:
        st.session_state[TRANSACTION_TYPE_KEY] = "All"
    if st.session_state[TRANSACTION_SORT_BY_KEY] not in SORT_BY_OPTIONS:
        st.session_state[TRANSACTION_SORT_BY_KEY] = "Date"
    if st.session_state[TRANSACTION_SORT_ORDER_KEY] not in SORT_ORDER_OPTIONS:
        st.session_state[TRANSACTION_SORT_ORDER_KEY] = "Descending"


def reset_transaction_filters() -> None:
    """Reset only Transactions-local filters without changing global dates."""

    for key, value in TRANSACTION_FILTER_DEFAULTS.items():
        st.session_state[key] = value
