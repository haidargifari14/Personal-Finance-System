"""Overview page for the Personal Finance Dashboard."""

import streamlit as st

from dashboard.components.charts import (
    cashflow_trend_chart,
    expense_by_category_chart,
    income_vs_expense_chart,
    monthly_trend_chart,
)
from dashboard.components.filters.global_filter import get_global_filter_values
from dashboard.components.filters.overview_filter import render_overview_filter
from dashboard.components.metric_cards import metric_card
from dashboard.components.tables import transaction_table
from dashboard.utils.formatter import (
    format_currency,
    format_datetime,
)
from services.account_service import AccountService
from services.analytics_service import AnalyticsService
from services.sheet_service import SheetService


def render() -> None:
    """Render the Overview page."""

    title_column, refresh_column = st.columns([5, 1], vertical_alignment="center")
    with title_column:
        st.title("Overview")

    with refresh_column:
        refresh_requested = st.button(
            "Refresh data",
            key="overview_refresh",
            width="stretch",
        )

    try:
        with st.spinner("Memuat data keuangan dari Google Sheets..."):
            analytics = AnalyticsService()
            if refresh_requested:
                analytics.clear_cache()
                SheetService.invalidate_read_cache(
                    "accounts",
                    "account_movements",
                )

            account_summary = AccountService(
                analytics.sheet_service
            ).get_current_balance_summary()

            categories = analytics.get_categories()
            start_date, end_date = get_global_filter_values()
            selected_categories, transaction_type = render_overview_filter(categories)

            summary = analytics.get_dashboard_summary(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
            )
            recent_transactions = analytics.get_recent_transactions(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
                limit=10,
            )
            income_expense_data = analytics.get_income_vs_expense(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
            )
            expense_by_category_data = analytics.get_expense_by_category(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
            )
            cashflow_trend_data = analytics.get_cashflow_trend(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
            )
            monthly_trend_data = analytics.get_monthly_trend(
                start_date=start_date,
                end_date=end_date,
                category=selected_categories,
                transaction_type=transaction_type,
            )
    except Exception:
        st.error("Gagal membaca data keuangan. Silakan coba lagi.")
        st.caption(
            "Periksa koneksi internet, akses Google Sheets, dan kredensial aplikasi."
        )
        return

    last_updated = analytics.get_last_loaded_at()
    last_updated_text = (
        format_datetime(last_updated) if last_updated is not None else "belum tersedia"
    )
    st.caption(f"Terakhir diperbarui: {last_updated_text}")
    st.divider()

    if summary["transaction_count"] == 0:
        st.info("Belum ada transaksi untuk filter yang dipilih.")

    _render_dashboard_kpis(summary, account_summary)

    st.divider()

    income_expense_column, category_column = st.columns(2)
    with income_expense_column:
        with st.container(border=True):
            st.subheader("Income vs Expense")
            income_vs_expense_chart(income_expense_data)

    with category_column:
        with st.container(border=True):
            st.subheader("Expense by Category")
            expense_by_category_chart(expense_by_category_data)

    with st.container(border=True):
        st.subheader("Cashflow Trend")
        cashflow_trend_chart(cashflow_trend_data)

    if len(monthly_trend_data) > 1:
        with st.container(border=True):
            st.subheader("Monthly Trend")
            monthly_trend_chart(monthly_trend_data)

    st.divider()

    with st.container(border=True):
        st.subheader("Recent Transactions")
        transaction_table(recent_transactions)

def _render_dashboard_kpis(summary: dict, account_summary: dict[str, int]) -> None:
    """Render current balance and filtered-period financial KPI cards."""

    primary_kpis = [
        (
            "Current balance",
            format_currency(account_summary["current_balance"]),
            f"{account_summary['active_account_count']} active account(s)",
        ),
        ("Income", format_currency(summary["income"])),
        ("Expense", format_currency(summary["expense"])),
        ("Net cashflow", format_currency(summary["net_cashflow"])),
    ]
    with st.container(horizontal=True):
        for item in primary_kpis:
            title, value, *delta = item
            metric_card(
                title,
                value,
                delta[0] if delta else None,
            )
