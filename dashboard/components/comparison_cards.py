"""Reusable comparison cards and tables for the Analytics page."""

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_percent


FINANCIAL_METRICS = {
    "income": "Income",
    "expense": "Expense",
    "saving": "Saving",
    "saving_rate": "Saving rate",
}
INDICATOR_LABELS = {
    "increase": "\u25B2 Increase",
    "decrease": "\u25BC Decrease",
    "no_change": "\u25AC No change",
}


def render_financial_comparison(data: dict[str, dict]) -> None:
    """Render current-versus-previous financial metrics as responsive cards."""

    with st.container(horizontal=True):
        for metric, label in FINANCIAL_METRICS.items():
            comparison = data[metric]
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.metric("Current period", _format_value(metric, comparison["current"]))
                st.caption(
                    f"Previous period: {_format_value(metric, comparison['previous'])}"
                )
                st.caption(
                    f"{INDICATOR_LABELS[comparison['indicator']]}: "
                    f"{_format_difference(metric, comparison['difference'])} "
                    f"({_format_percentage_change(comparison['percentage_change'])})"
                )


def render_category_comparison(data: pd.DataFrame) -> None:
    """Render expense category comparison data in a dashboard-ready table."""

    if data.empty:
        st.info("Belum ada data pengeluaran untuk dibandingkan.")
        return

    display_data = pd.DataFrame(
        {
            "Category": data["category"],
            "Current period": data["current_expense"].apply(format_currency),
            "Previous period": data["previous_expense"].apply(format_currency),
            "Difference": [
                f"{INDICATOR_LABELS[indicator]} "
                f"{_format_difference('expense', difference)}"
                for indicator, difference in zip(data["indicator"], data["difference"])
            ],
            "Change": data["percentage_change"].apply(_format_percentage_change),
        }
    )

    st.dataframe(
        display_data,
        width="stretch",
        height="auto",
        hide_index=True,
        column_config={
            "Category": st.column_config.TextColumn("Category", width="medium"),
            "Current period": st.column_config.TextColumn(
                "Current period", width="medium"
            ),
            "Previous period": st.column_config.TextColumn(
                "Previous period", width="medium"
            ),
            "Difference": st.column_config.TextColumn("Difference", width="large"),
            "Change": st.column_config.TextColumn("Change", width="small"),
        },
    )


def _format_value(metric: str, value: float | int) -> str:
    """Format a comparison metric value for display."""

    if metric == "saving_rate":
        return format_percent(value)
    return format_currency(value)


def _format_difference(metric: str, value: float | int) -> str:
    """Format a signed financial difference without recalculating it."""

    if metric == "saving_rate":
        return f"{value:+.2f} pp"

    sign = "+" if value > 0 else "-" if value < 0 else ""
    return f"{sign}{format_currency(abs(value))}"


def _format_percentage_change(value: float | None) -> str:
    """Format a safe percentage change value for display."""

    if pd.isna(value):
        return "New"
    return f"{value:+.2f}%"
