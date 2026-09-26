"""Reserved local filters for the Overview page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.filters._helpers import (
    TRANSACTION_TYPE_OPTIONS,
    category_options_for_type,
)

OVERVIEW_CATEGORY_KEY = "overview_categories"
OVERVIEW_TRANSACTION_TYPE_KEY = "overview_transaction_type"
_LEGACY_OVERVIEW_CATEGORY_KEY = "overview_category"


def _initialize_overview_filter_state(categories: list[str]) -> None:
    """Initialize Overview-owned multi-category and type filter state."""

    if st.session_state.get(OVERVIEW_TRANSACTION_TYPE_KEY) not in (
        TRANSACTION_TYPE_OPTIONS
    ):
        st.session_state[OVERVIEW_TRANSACTION_TYPE_KEY] = "All"

    legacy_category = st.session_state.pop(_LEGACY_OVERVIEW_CATEGORY_KEY, None)
    selected_categories = st.session_state.get(OVERVIEW_CATEGORY_KEY)

    if not isinstance(selected_categories, list):
        candidate = selected_categories or legacy_category
        selected_categories = []
        if isinstance(candidate, str) and candidate not in ("", "All"):
            selected_categories = [candidate]

    st.session_state[OVERVIEW_CATEGORY_KEY] = [
        category for category in selected_categories if category in categories
    ]

def render_overview_filter(categories: list[str]) -> tuple[list[str], str]:
    """Render Overview's multi-category and transaction-type filters."""

    if st.session_state.get(OVERVIEW_TRANSACTION_TYPE_KEY) not in (
        TRANSACTION_TYPE_OPTIONS
    ):
        st.session_state[OVERVIEW_TRANSACTION_TYPE_KEY] = "All"
    transaction_type = st.session_state.get(OVERVIEW_TRANSACTION_TYPE_KEY, "All")
    available_categories = category_options_for_type(categories, transaction_type)
    _initialize_overview_filter_state(available_categories)

    with st.container(border=False, key="overview-filters"):
        st.caption("Overview filters")
        with st.container(horizontal=True):
            transaction_type = st.selectbox(
                "Transaction type",
                options=TRANSACTION_TYPE_OPTIONS,
                key=OVERVIEW_TRANSACTION_TYPE_KEY,
                persist_state="session",
            )
            selected_categories = st.multiselect(
                "Categories",
                options=available_categories,
                key=OVERVIEW_CATEGORY_KEY,
                placeholder="All Categories",
                help="Kosong berarti All Categories.",
            )

        if not selected_categories:
            st.caption("All Categories")

    return selected_categories, transaction_type
