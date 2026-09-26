"""Analytics page for the Personal Finance Dashboard."""

from __future__ import annotations

from html import escape

import streamlit as st

from dashboard.components.category_cards import (
    render_category_cards,
    render_category_summary_cards,
)
from dashboard.components.charts import category_monthly_trend_chart
from dashboard.components.comparison_cards import (
    render_category_comparison,
    render_financial_comparison,
)
from dashboard.components.filters.analytics_filter import (
    get_analytics_filter_values,
    render_analytics_filter,
)
from dashboard.components.filters.global_filter import get_global_filter_values
from dashboard.components.icons import material_icon
from dashboard.components.statistics_cards import render_financial_statistics
from dashboard.components.tables import category_transaction_table
from dashboard.utils.formatter import format_date
from services.analytics_service import AnalyticsService


def render() -> None:
    """Render Analytics in the approved general-to-detail information flow."""

    st.title("Analytics")
    st.caption("Understand where your money goes and how your spending changes.")

    try:
        with st.spinner("Memuat analisis pengeluaran..."):
            analytics = AnalyticsService()
            categories = analytics.get_categories()
            start_date, end_date = get_global_filter_values()
            category, transaction_type = get_analytics_filter_values(categories)
            financial_statistics = analytics.get_financial_statistics(
                start_date=start_date,
                end_date=end_date,
                category=category,
                transaction_type=transaction_type,
            )
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

    with st.container(border=False, key="analytics-statistics"):
        st.markdown(
            _section_title("1. Financial Statistics", "query_stats"),
            unsafe_allow_html=True,
        )
        render_financial_statistics(financial_statistics)

    render_analytics_filter(categories)

    with st.container(border=False, key="analytics-top-categories"):
        st.markdown(
            _section_title("3. Top 3 Spending Categories", "workspace_premium"),
            unsafe_allow_html=True,
        )
        selected_category = render_category_cards(top_spending_categories)
        st.caption("Tap a category to see more details and insights.")

    if selected_category is None:
        with st.container(border=False, key="analytics-category-detail"):
            st.markdown(
                _section_title("4. Category Detail", "category"),
                unsafe_allow_html=True,
            )
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


def _render_category_detail(category_detail: dict[str, object]) -> None:
    """Render selected-category detail using service-provided values only."""

    summary = category_detail["summary"]
    category_name = summary["category"]

    with st.container(border=False, key="analytics-category-detail"):
        st.markdown(
            _section_title(
                f"4. Category Detail — {escape(str(category_name))}",
                "category",
            ),
            unsafe_allow_html=True,
        )

        if summary["transaction_count"] == 0:
            st.info("Belum ada transaksi untuk kategori yang dipilih.")
            return

        render_category_summary_cards(summary)

        trend_column, transaction_column = st.columns(2)
        with trend_column:
            with st.container(border=False, key="analytics-monthly-trend"):
                st.markdown(
                    _subsection_title("Monthly Trend", "show_chart"),
                    unsafe_allow_html=True,
                )
                category_monthly_trend_chart(category_detail["monthly_trend"])
        with transaction_column:
            with st.container(border=False, key="analytics-category-transactions"):
                st.markdown(
                    _subsection_title("Recent Transactions", "receipt_long"),
                    unsafe_allow_html=True,
                )
                category_transaction_table(category_detail["transactions"])


def _render_period_comparison(period_comparison: dict[str, object]) -> None:
    """Render the service-provided current-versus-previous period comparison."""

    current_period = period_comparison["current_period"]
    previous_period = period_comparison["previous_period"]

    with st.container(border=False, key="analytics-period-comparison"):
        st.markdown(
            _section_title("5. Period Comparison", "compare_arrows"),
            unsafe_allow_html=True,
        )
        st.caption(
            "Current period: "
            f"{format_date(current_period['start_date'])} - "
            f"{format_date(current_period['end_date'])} | "
            "Previous period: "
            f"{format_date(previous_period['start_date'])} - "
            f"{format_date(previous_period['end_date'])}"
        )
        financial_column, category_column = st.columns([1, 1.25])
        with financial_column:
            with st.container(border=False, key="analytics-financial-comparison"):
                st.markdown(
                    _subsection_title("Financial Comparison", "account_balance"),
                    unsafe_allow_html=True,
                )
                render_financial_comparison(period_comparison["financial_comparison"])
        with category_column:
            with st.container(border=False, key="analytics-category-comparison"):
                st.markdown(
                    _subsection_title("Category Comparison", "category"),
                    unsafe_allow_html=True,
                )
                render_category_comparison(period_comparison["category_comparison"])


def _section_title(title: str, icon: str) -> str:
    """Return a consistent Analytics section heading without changing layout."""

    return (
        "<div class=\"pf-analytics-section-title\">"
        f"{material_icon(icon)}{title}</div>"
    )


def _subsection_title(title: str, icon: str) -> str:
    """Return a compact icon-led Analytics subsection heading."""

    return (
        "<div class=\"pf-analytics-subsection-title\">"
        f"{material_icon(icon)}{title}</div>"
    )
