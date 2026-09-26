"""Reusable comparison cards and tables for the Analytics page."""

from html import escape

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_percent


FINANCIAL_METRICS = {
    "income": "Income",
    "expense": "Expense",
    "saving": "Saving",
    "saving_rate": "Saving rate",
}
INDICATOR_SYMBOLS = {
    "increase": "↑",
    "decrease": "↓",
    "no_change": "—",
}


def render_financial_comparison(data: dict[str, dict]) -> None:
    """Render current-versus-previous metrics in a responsive two-by-two grid."""

    metrics = tuple(FINANCIAL_METRICS.items())
    for row_metrics in (metrics[:2], metrics[2:]):
        _render_financial_comparison_row(data, row_metrics)


def _render_financial_comparison_row(
    data: dict[str, dict],
    row_metrics: tuple[tuple[str, str], ...],
) -> None:
    """Render one responsive two-card Financial Comparison row."""

    for column, (metric, label) in zip(st.columns(2), row_metrics):
        with column:
            comparison = data[metric]
            state = _comparison_state(metric, comparison)
            st.markdown(
                "<div class=\"pf-comparison-card pf-comparison-card--{state}\">"
                "<div class=\"pf-comparison-card__title\">{title}</div>"
                "<div class=\"pf-comparison-card__current\">{current}</div>"
                "<div class=\"pf-comparison-card__previous\">Previous: {previous}</div>"
                "<div class=\"pf-comparison-card__change\">{change}</div></div>".format(
                    state=escape(state),
                    title=escape(label),
                    current=escape(_format_value(metric, comparison["current"])),
                    previous=escape(_format_value(metric, comparison["previous"])),
                    change=escape(_financial_change_copy(comparison)),
                ),
                unsafe_allow_html=True,
            )


def render_category_comparison(data: pd.DataFrame) -> None:
    """Render a concise three-column expense-category comparison table."""

    if data.empty:
        st.info("Belum ada data pengeluaran untuk dibandingkan.")
        return

    rows = []
    for row in data.itertuples(index=False):
        change, state = _category_change_copy(
            row.difference,
            row.percentage_change,
            row.indicator,
        )
        rows.append(
            "<tr><td>{category}</td><td>{current}</td>"
            "<td class=\"pf-category-comparison__change--{state}\">{change}</td>"
            "</tr>".format(
                category=escape(str(row.category)),
                current=escape(format_currency(int(row.current_expense))),
                state=escape(state),
                change=escape(change),
            )
        )

    st.markdown(
        "<table class=\"pf-category-comparison\"><thead><tr>"
        "<th>Category</th><th>Current period</th><th>Difference</th>"
        "</tr></thead><tbody>{rows}</tbody></table>".format(rows="".join(rows)),
        unsafe_allow_html=True,
    )


def _format_value(metric: str, value: float | int) -> str:
    """Format a comparison metric value for display."""

    if metric == "saving_rate":
        return format_percent(value)
    return format_currency(value)


def _financial_change_copy(comparison: dict) -> str:
    """Return concise copy for an already-calculated financial comparison."""

    percentage_change = comparison["percentage_change"]
    if percentage_change is None or pd.isna(percentage_change):
        return "New" if comparison["current"] != 0 else "No previous data"
    if comparison["difference"] == 0:
        return "No change"
    return (
        f"{INDICATOR_SYMBOLS[comparison['indicator']]} "
        f"{percentage_change:+.2f}% vs previous"
    )


def _category_change_copy(
    difference: float | int,
    percentage_change: float | None,
    indicator: str,
) -> tuple[str, str]:
    """Format expense change with expense-aware semantic color treatment."""

    if percentage_change is None or pd.isna(percentage_change):
        return ("New" if difference != 0 else "—", "neutral")
    if difference == 0:
        return "—", "neutral"
    state = "negative" if difference > 0 else "positive"
    return f"{INDICATOR_SYMBOLS[indicator]} {percentage_change:+.2f}%", state


def _comparison_state(metric: str, comparison: dict) -> str:
    """Return a display-only semantic state without changing comparison facts."""

    if comparison["percentage_change"] is None or pd.isna(
        comparison["percentage_change"]
    ):
        return "neutral"
    if comparison["difference"] == 0:
        return "neutral"

    improvement = comparison["difference"] > 0
    if metric == "expense":
        improvement = not improvement
    return "positive" if improvement else "negative"
