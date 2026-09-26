"""
dashboard/utils/theme.py

Centralized UI theme configuration for the Personal Finance Dashboard.

All visual constants should be defined here to keep the dashboard
consistent and easy to maintain.
"""

# ==========================================================
# Color Palette
# ==========================================================

PRIMARY_COLOR = "#D97742"      # Terracotta
SUCCESS_COLOR = "#37A86B"      # Sage green
WARNING_COLOR = "#D89A35"      # Warm amber
DANGER_COLOR = "#D85C59"       # Muted coral red
INFO_COLOR = "#6B8FC7"         # Dusty blue

BACKGROUND_COLOR = "#F7F0E8"
SURFACE_COLOR = "#FCF8F3"

TEXT_PRIMARY = "#332621"
TEXT_SECONDARY = "#806F66"

BORDER_COLOR = "#E1CFC1"


# ==========================================================
# Layout
# ==========================================================

DEFAULT_PADDING = 20

SECTION_SPACING = 24

CARD_BORDER_RADIUS = 12

CARD_HEIGHT = 140

SIDEBAR_WIDTH = 280


# ==========================================================
# Chart
# ==========================================================

CHART_HEIGHT = 320

PIE_CHART_HEIGHT = 240


# ==========================================================
# Table
# ==========================================================

TABLE_HEIGHT = 420


# ==========================================================
# Metric Card
# ==========================================================

METRIC_ICON_SIZE = 24

METRIC_VALUE_SIZE = 30

METRIC_LABEL_SIZE = 14


# ==========================================================
# Currency
# ==========================================================

CURRENCY_SYMBOL = "Rp"


# ==========================================================
# Date Format
# ==========================================================

DEFAULT_DATE_FORMAT = "%d %b %Y"


def apply_warm_light_theme() -> None:
    """Inject the shared warm-light visual treatment for the dashboard."""

    from pathlib import Path

    import streamlit as st

    stylesheet = Path(__file__).parents[1] / "assets" / "style.css"
    st.markdown(
        f"<style>{stylesheet.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )
