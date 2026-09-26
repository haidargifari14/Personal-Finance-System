"""Overview page for the Personal Finance Dashboard."""

import streamlit as st

from dashboard.components.charts import (
    cashflow_trend_chart,
    expense_by_category_chart,
)
from dashboard.components.filters.global_filter import get_global_filter_values
from dashboard.components.filters.overview_filter import render_overview_filter
from dashboard.components.overview_cards import (
    render_account_balance_snapshot,
    render_overview_kpi,
)
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

    title_column, updated_column, refresh_column = st.columns(
        [4.5, 1.6, 1],
        vertical_alignment="center",
    )
    with title_column:
        st.title("Overview")
        st.caption("Your financial summary at a glance")

    with updated_column:
        last_updated_slot = st.empty()

    with refresh_column:
        refresh_requested = st.button(
            "Refresh data",
            key="overview_refresh",
            icon=":material/refresh:",
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

            account_service = AccountService(analytics.sheet_service)
            account_summary = account_service.get_current_balance_summary()
            account_summaries = account_service.get_account_summaries()

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
    last_updated_slot.caption(f"↻ Last updated: {last_updated_text}")

    if summary["transaction_count"] == 0:
        st.info("Belum ada transaksi untuk filter yang dipilih.")

    _render_dashboard_kpis(summary, account_summary)

    account_column, category_column = st.columns([1, 1.35])
    with account_column:
        with st.container(border=False, key="overview-insight"):
            render_account_balance_snapshot(account_summaries)

    with category_column:
        with st.container(border=False, key="overview-insight-category"):
            st.markdown(
                "<div class=\"pf-section-heading\">"
                "<span class=\"pf-section-heading__title\">◌ Expense by Category</span>"
                "<span class=\"pf-section-heading__meta\">Selected period</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            expense_by_category_chart(expense_by_category_data)

    with st.container(border=False, key="overview-trend"):
        st.markdown(
            "<div class=\"pf-section-heading\">"
            "<span class=\"pf-section-heading__title\">⌁ Cashflow Trend</span>"
            "<span class=\"pf-section-heading__meta\">Income and Expense by day</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        cashflow_trend_chart(cashflow_trend_data)

    with st.container(border=False, key="overview-transactions"):
        st.markdown(
            "<div class=\"pf-section-heading\">"
            "<span class=\"pf-section-heading__title\">▤ Recent Transactions</span>"
            "<span class=\"pf-section-heading__meta\">Latest 10 records</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        transaction_table(recent_transactions)


def _render_dashboard_kpis(summary: dict, account_summary: dict[str, int]) -> None:
    """Render current balance and filtered-period financial KPI cards."""

    current, income, expense, cashflow = st.columns([1.5, 1, 1, 1])
    with current:
        with st.container(border=False, key="overview-kpi-current"):
            render_overview_kpi(
                title="Current balance",
                value=format_currency(account_summary["current_balance"]),
                variant="current",
                metadata=f"{account_summary['active_account_count']} active account(s)",
            )
    with income:
        with st.container(border=False, key="overview-kpi-income"):
            render_overview_kpi(
                title="Income",
                value=format_currency(summary["income"]),
                variant="income",
                metadata="Selected period",
            )
    with expense:
        with st.container(border=False, key="overview-kpi-expense"):
            render_overview_kpi(
                title="Expense",
                value=format_currency(summary["expense"]),
                variant="expense",
                metadata="Selected period",
            )
    with cashflow:
        with st.container(border=False, key="overview-kpi-cashflow"):
            render_overview_kpi(
                title="Net cashflow",
                value=format_currency(summary["net_cashflow"]),
                variant="cashflow",
                metadata="Selected period",
                is_negative=summary["net_cashflow"] < 0,
            )
