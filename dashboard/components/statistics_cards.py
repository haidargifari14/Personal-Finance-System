"""Reusable Financial Statistics cards for the Analytics page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.metric_cards import metric_card
from dashboard.utils.formatter import format_currency, format_percent


def render_financial_statistics(
    statistics: dict[str, int | float | None],
) -> None:
    """Render service-provided Financial Statistics in grouped metric cards."""

    if statistics["transaction_count"] == 0:
        st.info("Belum ada transaksi untuk menampilkan statistik keuangan.")
        return

    st.markdown("**Income**")
    with st.container(horizontal=True):
        _statistic_card(
            "Average income",
            statistics["average_income"],
            "Belum ada transaksi income.",
        )
        _statistic_card(
            "Largest income",
            statistics["largest_income"],
            "Belum ada transaksi income.",
        )

    st.markdown("**Expense**")
    with st.container(horizontal=True):
        _statistic_card(
            "Average expense",
            statistics["average_expense"],
            "Belum ada transaksi expense.",
        )
        _statistic_card(
            "Largest expense",
            statistics["largest_expense"],
            "Belum ada transaksi expense.",
        )

    st.markdown("**General**")
    with st.container(horizontal=True):
        _statistic_card(
            "Average saving",
            statistics["average_saving"],
            "Belum ada transaksi untuk menghitung saving.",
        )
        _ratio_card(statistics["expense_income_ratio"])
        _statistic_card(
            "Average transaction value",
            statistics["average_transaction_value"],
            "Belum ada transaksi.",
        )
        metric_card("Total transactions", str(statistics["transaction_count"]))


def _statistic_card(title: str, value: int | float | None, empty_text: str) -> None:
    """Render a currency statistic card or an explicit unavailable state."""

    if value is None:
        metric_card(title, "—", help_text=empty_text)
        return

    metric_card(title, _format_signed_currency(value))


def _ratio_card(value: int | float | None) -> None:
    """Render the safe Expense-to-Income ratio card."""

    if value is None:
        metric_card(
            "Expense / income ratio",
            "—",
            help_text="Rasio tersedia setelah ada transaksi income.",
        )
        return

    metric_card("Expense / income ratio", format_percent(value))


def _format_signed_currency(value: int | float) -> str:
    """Format negative amounts with a leading minus sign before Rupiah."""

    if value < 0:
        return f"-{format_currency(abs(value))}"

    return format_currency(value)
