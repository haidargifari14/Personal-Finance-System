"""Reusable Settings card for safe external integration information."""

from __future__ import annotations

import streamlit as st

from dashboard.utils.formatter import format_datetime
from services.integration_service import IntegrationStatus


def render_integration_card(status: IntegrationStatus, *, key: str) -> bool:
    """Render one integration status card and return a recheck request."""

    with st.container(border=True):
        st.subheader(status.name)
        _render_status(status)
        for label, value in status.details.items():
            st.caption(label)
            st.write(value)
        if status.checked_at:
            st.caption(f"Last checked: {format_datetime(status.checked_at)}")
        if status.message:
            st.caption(status.message)
        return st.button(
            "Test connection",
            key=f"{key}_test_connection",
            icon=":material/network_check:",
            width="content",
        )


def _render_status(status: IntegrationStatus) -> None:
    """Render a clear native Streamlit status indicator."""

    status_text = f"Status: {status.state}"
    if status.state == "Connected":
        st.success(status_text)
    elif status.state in {"Error", "Not Configured"}:
        st.error(status_text)
    else:
        st.warning(status_text)
