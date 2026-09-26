"""Sidebar navigation for the Personal Finance Dashboard."""

from __future__ import annotations

import streamlit as st

from dashboard.components.filters.global_filter import render_global_filter

PAGE_OPTIONS = (
    "Overview",
    "Analytics",
    "Transactions",
    "Forecast",
    "Profile",
    "Settings",
)

NAVIGATION_ICONS = {
    "Overview": "⌂",
    "Analytics": "▥",
    "Transactions": "☷",
    "Forecast": "⌁",
    "Profile": "♙",
    "Settings": "⚙",
}


def render_sidebar() -> str:
    """Render responsive dashboard navigation and return the active page."""

    with st.sidebar:
        st.markdown(
            "<div class=\"pf-sidebar-brand\">"
            "<span class=\"pf-sidebar-brand__icon\">💰</span>"
            "<span>Personal Finance</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Navigation",
            PAGE_OPTIONS,
            format_func=lambda option: f"{NAVIGATION_ICONS[option]}  {option}",
        )

    render_global_filter()

    return page
