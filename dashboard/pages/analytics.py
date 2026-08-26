"""Analytics page for the Personal Finance Dashboard."""

import streamlit as st

from dashboard.components.category_cards import render_category_cards
from dashboard.components.charts import category_monthly_trend_chart
from dashboard.components.comparison_cards import (
    render_category_comparison,
    render_financial_comparison,
)
from dashboard.components.filters.analytics_filter import render_analytics_filter
from dashboard.components.filters.global_filter import get_global_filter_values
from dashboard.components.metric_cards import metric_card
from dashboard.components.statistics_cards import render_financial_statistics
from dashboard.components.tables import transaction_table
from dashboard.utils.formatter import format_currency, format_date, format_percent
from services.analytics_service import AnalyticsService


def render() -> None:
    """Render the Analytics page and its top spending category entry point."""

    st.title("Analytics")

    try:
        with st.spinner("Memuat analisis pengeluaran..."):
            analytics = AnalyticsService()
            categories = analytics.get_categories()
            start_date, end_date = get_global_filter_values()
            category, transaction_type = render_analytics_filter(categories)
            top_spending_categories = analytics.get_top_spending_categories(
                start_date=start_date,
                end_date=end_date,
                category=category,
                transaction_type=transaction_type,
            )
    except Exception:
        st.error("Gagal membaca data analisis. Silakan coba lagi.")
        st.caption(
            "Periksa koneksi internet, akses Google Sheets, dan kredensial aplikasi."
        )
        return

    with st.container(border=True):
        st.subheader("Top Spending Categories")
        selected_category = render_category_cards(top_spending_categories)

    st.divider()

    if selected_category is None:
        st.subheader("Category Detail")
        st.info("Pilih kategori pengeluaran untuk melihat detailnya.")
    else:
        try:
            with st.spinner("Memuat detail kategori..."):
                category_detail = analytics.get_category_drilldown(
                    selected_category,
                    start_date=start_date,
                    end_date=end_date,
                    category=category,
                    transaction_type=transaction_type,
                )
        except Exception:
            st.error("Gagal memuat detail kategori. Silakan coba lagi.")
            return

        _render_category_detail(category_detail)

    try:
        with st.spinner("Membandingkan periode keuangan..."):
            period_comparison = analytics.get_period_comparison(
                start_date=start_date,
                end_date=end_date,
                category=category,
                transaction_type=transaction_type,
            )
    except Exception:
        st.error("Gagal membandingkan periode keuangan. Silakan coba lagi.")
        return

    _render_period_comparison(period_comparison)

    try:
        with st.spinner("Memuat statistik keuangan..."):
            financial_statistics = analytics.get_financial_statistics(
                start_date=start_date,
                end_date=end_date,
                category=category,
                transaction_type=transaction_type,
            )
    except Exception:
        st.error("Gagal memuat statistik keuangan. Silakan coba lagi.")
        return

    _render_financial_statistics(financial_statistics)


def _render_category_detail(category_detail: dict[str, object]) -> None:
    """Render the selected category's service-provided drilldown data."""

    summary = category_detail["summary"]

    st.subheader("Category Detail")
    st.markdown(f"#### {summary['category']}")

    if summary["transaction_count"] == 0:
        st.info("Belum ada transaksi untuk kategori yang dipilih.")
        return

    with st.container(horizontal=True):
        metric_card("Total expense", format_currency(summary["total_expense"]))
        metric_card("Average expense", format_currency(summary["average_expense"]))
        metric_card("Highest expense", format_currency(summary["highest_expense"]))
        metric_card("Transaction count", str(summary["transaction_count"]))
        metric_card("Contribution", format_percent(summary["contribution"]))

    with st.container(border=True):
        st.subheader("Monthly Trend")
        category_monthly_trend_chart(category_detail["monthly_trend"])

    with st.container(border=True):
        st.subheader("Recent Transactions")
        transaction_table(category_detail["transactions"])


def _render_period_comparison(period_comparison: dict[str, object]) -> None:
    """Render the service-provided current-versus-previous period comparison."""

    current_period = period_comparison["current_period"]
    previous_period = period_comparison["previous_period"]

    st.divider()
    st.subheader("Period Comparison")
    st.caption(
        "Current period: "
        f"{format_date(current_period['start_date'])} - "
        f"{format_date(current_period['end_date'])} | "
        "Previous period: "
        f"{format_date(previous_period['start_date'])} - "
        f"{format_date(previous_period['end_date'])}"
    )

    with st.container(border=True):
        st.markdown("**Financial Comparison**")
        render_financial_comparison(period_comparison["financial_comparison"])

    with st.container(border=True):
        st.markdown("**Category Comparison**")
        render_category_comparison(period_comparison["category_comparison"])


def _render_financial_statistics(
    financial_statistics: dict[str, int | float | None],
) -> None:
    """Render filtered Financial Statistics as the final Analytics section."""

    st.divider()
    st.subheader("Financial Statistics")
    with st.container(border=True):
        render_financial_statistics(financial_statistics)
