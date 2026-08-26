"""Reserved local filters for the Analytics page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.filters._helpers import (
    TRANSACTION_TYPE_OPTIONS,
    category_options_for_type,
    initialize_local_filter_state,
)

ANALYTICS_CATEGORY_KEY = "analytics_category"
ANALYTICS_TRANSACTION_TYPE_KEY = "analytics_transaction_type"


def render_analytics_filter(categories: list[str]) -> tuple[str, str]:
    """Render local Category and Transaction Type filters for Analytics."""

    if st.session_state.get(ANALYTICS_TRANSACTION_TYPE_KEY) not in (
        TRANSACTION_TYPE_OPTIONS
    ):
        st.session_state[ANALYTICS_TRANSACTION_TYPE_KEY] = "All"

    transaction_type = st.session_state[ANALYTICS_TRANSACTION_TYPE_KEY]
    available_categories = ["All", *category_options_for_type(
        categories,
        transaction_type,
    )]
    initialize_local_filter_state(
        ANALYTICS_CATEGORY_KEY,
        ANALYTICS_TRANSACTION_TYPE_KEY,
        available_categories,
    )

    with st.container(border=True):
        st.caption("Analytics filters")
        with st.container(horizontal=True):
            transaction_type = st.selectbox(
                "Transaction type",
                options=TRANSACTION_TYPE_OPTIONS,
                key=ANALYTICS_TRANSACTION_TYPE_KEY,
                persist_state="session",
            )
            category = st.selectbox(
                "Category",
                options=available_categories,
                key=ANALYTICS_CATEGORY_KEY,
                persist_state="session",
            )

    return category, transaction_type
