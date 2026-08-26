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


def render_sidebar() -> str:
    """Render responsive dashboard navigation and return the active page."""

    with st.sidebar:
        st.title("💰 Personal Finance")
        page = st.radio("Navigation", PAGE_OPTIONS)

    render_global_filter()

    return page
