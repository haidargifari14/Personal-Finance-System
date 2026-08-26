"""Reusable toolbar components for dashboard workspaces."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_transaction_toolbar(
    search_key: str,
) -> tuple[str, bool, bool, Any]:
    """Render the Transactions toolbar and return search and button intents."""

    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.text_input(
                "Search transactions",
                placeholder="Search category or note",
                icon=":material/search:",
                key=search_key,
                width="stretch",
                persist_state="session",
            )
            add_requested = st.button(
                "Add transaction",
                icon=":material/add:",
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

    return (
        st.session_state[search_key],
        add_requested,
        refresh_requested,
        export_container,
    )
