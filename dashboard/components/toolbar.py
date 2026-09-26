"""Reusable controls for the Transactions workspace."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_transaction_toolbar() -> tuple[bool, bool, Any]:
    """Render compact Transactions actions and return their intents."""

    with st.container(horizontal=True, vertical_alignment="center"):
        add_requested = st.button(
            "Add transaction",
            icon=":material/add:",
            key="transactions_add",
            type="primary",
        )
        export_container = st.popover(
            "Export",
            icon=":material/download:",
            on_change="rerun",
        )
        refresh_requested = st.button(
            "Refresh",
            key="transactions_refresh",
            icon=":material/refresh:",
        )

    return add_requested, refresh_requested, export_container


def render_transaction_search(search_key: str) -> str:
    """Render the dedicated operational search input."""

    st.text_input(
        "Search transactions",
        placeholder="Search category or note",
        icon=":material/search:",
        key=search_key,
        width="stretch",
        persist_state="session",
    )
    return str(st.session_state[search_key])
