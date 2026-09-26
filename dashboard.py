"""
dashboard.py

Entry point for the Personal Finance Dashboard.
"""

import streamlit as st

from dashboard.components.sidebar import render_sidebar
from dashboard.utils.theme import apply_warm_light_theme
from services.sheet_service import SheetService

from dashboard.pages import (
    overview,
    analytics,
    transactions,
    forecast,
    profile,
    settings,
)

# ==========================================================
# Streamlit Configuration
# ==========================================================

st.set_page_config(
    page_title="Personal Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_warm_light_theme()

# ==========================================================
# Dashboard Routing
# ==========================================================

PAGES = {
    "Overview": overview.render,
    "Analytics": analytics.render,
    "Transactions": transactions.render,
    "Forecast": forecast.render,
    "Profile": profile.render,
    "Settings": settings.render,
}

# ==========================================================
# Render Selected Page
# ==========================================================

selected_page = render_sidebar()

PAGES[selected_page]()

stale_datasets = [
    name
    for name, status in SheetService.get_read_cache_status().items()
    if bool(status["is_stale"])
]
if stale_datasets:
    st.warning(
        "Google Sheets sementara tidak tersedia. Menampilkan data terakhir yang "
        "berhasil dimuat; beberapa informasi mungkin belum terbaru."
    )
