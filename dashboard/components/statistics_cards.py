"""Compact Financial Statistics cards for the Analytics page."""

from __future__ import annotations

from html import escape

import streamlit as st

from dashboard.components.icons import material_icon
from dashboard.utils.formatter import format_currency


def render_financial_statistics(
    statistics: dict[str, int | float | None],
) -> None:
    """Render the four approved service-provided Analytics statistics.

    Args:
        statistics: Already-calculated values returned by ``AnalyticsService``.
    """

    if statistics["transaction_count"] == 0:
        st.info("Belum ada transaksi untuk menampilkan statistik keuangan.")
        return

    cards = (
        (
            "Income",
            _format_currency(statistics["income"]),
            "income",
            "south",
            "Active period",
        ),
        (
            "Expense this period",
            _format_currency(statistics["expense"]),
            "expense-period",
            "monitor_heart",
            "Active period",
        ),
        (
            "Largest expense",
            _format_currency(statistics["largest_expense"]),
            "largest-expense",
            "north",
            "Active period",
        ),
        (
            "Total transactions",
            str(statistics["transaction_count"]),
            "transactions",
            "receipt_long",
            "Active period",
        ),
    )

    columns = st.columns(4)
    for column, (title, value, variant, icon, metadata) in zip(columns, cards):
        with column:
            st.markdown(
                "<div class=\"pf-analytics-stat pf-analytics-stat--{variant}\">"
                "<div class=\"pf-analytics-stat__topline\">"
                "<span class=\"pf-analytics-stat__icon\">{icon}</span>"
                "<div class=\"pf-analytics-stat__label\">{title}</div></div>"
                "<div class=\"pf-analytics-stat__value\">{value}</div>"
                "<div class=\"pf-analytics-stat__meta\">{metadata}</div>"
                "</div>".format(
                    title=escape(title),
                    value=escape(value),
                    variant=escape(variant),
                    icon=material_icon(icon),
                    metadata=escape(metadata),
                ),
                unsafe_allow_html=True,
            )


def _format_currency(value: int | float | None) -> str:
    """Format an optional service value without changing its meaning."""

    return "—" if value is None else format_currency(value)
