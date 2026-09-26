"""Reusable Settings card for safe external integration information."""

from __future__ import annotations

import streamlit as st

from dashboard.utils.formatter import format_datetime
from services.integration_service import IntegrationStatus


def render_integration_card(status: IntegrationStatus, *, key: str) -> bool:
    """Render one integration status card and return a recheck request."""

    icon, purpose = _integration_presentation(status.name)
    with st.container(border=True, key=f"{key}_card"):
        heading, state = st.columns([4, 1], vertical_alignment="center")
        with heading:
            st.markdown(
                "<div class=\"pf-integration-card__heading\">"
                f"<span class=\"material-symbols-rounded\">{icon}</span>"
                f"<span>{status.name}</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(purpose)
        with state:
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


def _integration_presentation(name: str) -> tuple[str, str]:
    """Return UI-only icon and purpose copy for known integrations."""

    if name == "Telegram Bot":
        return "send", "Used for transaction input"
    if name == "Google Sheets":
        return "table_view", "Workbook availability and data sync"
    return "extension", "Application integration"


def _render_status(status: IntegrationStatus) -> None:
    """Render a clear native Streamlit status indicator."""

    semantic_state = {
        "Connected": "connected",
        "Error": "error",
        "Not Configured": "error",
    }.get(status.state, "warning")
    st.markdown(
        f'<span class="pf-integration-status pf-integration-status--{semantic_state}">'
        f"{status.state}</span>",
        unsafe_allow_html=True,
    )
