"""Presentation-only components for Forecast V2 results."""

from __future__ import annotations

from typing import Mapping, Sequence

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency
from models.account import Account
from models.goal import Goal


def render_financial_outlook(
    outlook: Mapping[str, object],
    spending_limit_status: Mapping[str, object],
    expense_forecast: Mapping[str, object],
) -> None:
    """Render the service-provided global Financial Outlook only."""

    with st.container(border=True):
        st.subheader("Financial Outlook")
        first, second, third, fourth = st.columns(4)
        first.metric(
            "Current Balance",
            format_currency(int(outlook["current_balance"])),
            help="Jumlah saldo seluruh Account aktif.",
        )
        second.metric(
            "Projected Normalized Monthly Spending",
            format_currency(
                int(spending_limit_status["projected_normalized_monthly_spending"])
            ),
            help="Pengeluaran Normalized bulan ini ditambah proyeksi seluruh kategori yang dapat di-forecast.",
        )
        third.metric(
            "Global Projected Remaining Spending",
            format_currency(int(outlook["global_projected_remaining_spending"])),
            help="Proyeksi expense masa depan dari semua kategori dengan forecast yang usable.",
        )
        fourth.metric(
            "Global Estimated Balance",
            format_currency(int(outlook["global_estimated_balance"])),
            help="Current Balance dikurangi Global Projected Remaining Spending.",
        )
        _render_outlook_status(outlook, spending_limit_status)
        st.caption(str(outlook["global_category_inclusion_rules"]))
    render_calculation_details(outlook, spending_limit_status, expense_forecast)


def _render_outlook_status(
    outlook: Mapping[str, object],
    spending_limit_status: Mapping[str, object],
) -> None:
    """Render service-derived Spending and Balance risk states."""

    if bool(spending_limit_status.get("configured", False)):
        if bool(spending_limit_status.get("spending_risk", False)):
            st.warning(
                "Spending Risk: projected normalized spending exceeds the Monthly Spending Limit.",
                icon="⚠️",
            )
        else:
            st.success("Within Monthly Spending Limit.", icon="✅")
    else:
        st.caption("Monthly Spending Limit has not been configured.")
    if bool(outlook.get("balance_risk", False)):
        st.error("Critical Balance Risk: global estimated balance is below zero.")
    else:
        st.caption("No Balance Risk in the global Financial Outlook.")


def render_calculation_details(
    outlook: Mapping[str, object],
    spending_limit_status: Mapping[str, object],
    expense_forecast: Mapping[str, object],
) -> None:
    """Render audit facts from precomputed results without data access."""

    with st.expander("Calculation Details", expanded=False):
        st.markdown("**Expense classification breakdown**")
        breakdown = expense_forecast.get("classification_breakdown", {})
        classification_rows = [
            ("Actual Cash Expense This Month", "actual_cash_expense_this_month"),
            ("Normal Expense Contribution", "normal_expense_contribution"),
            ("Periodic Raw Expense", "periodic_raw_expense"),
            ("Periodic Monthly Equivalent", "periodic_monthly_equivalent"),
            ("One-off Expense", "one_off_expense"),
            ("One-off Excluded Amount", "one_off_excluded_amount"),
            ("Normalized Spending So Far", "normalized_spending_so_far"),
        ]
        st.dataframe(
            pd.DataFrame(
                [
                    {"Metric": label, "Amount": format_currency(int(breakdown.get(key, 0)))}
                    for label, key in classification_rows
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("**Category forecast breakdown**")
        category_rows = []
        for item in expense_forecast.get("categories", []):
            category_rows.append(
                {
                    "Category": item["category"],
                    "Forecast Status": item["forecast_data_quality"],
                    "Coverage Days": item["historical_coverage_days"],
                    "Transaction Count": item["training_transaction_count"],
                    "Active Days": item["active_days"],
                    "Training Spending": format_currency(
                        int(item["training_spending"])
                    ),
                    "Average Daily Spending": (
                        format_currency(float(item["average_daily_spending"]))
                        if item["average_daily_spending"] is not None
                        else "N/A"
                    ),
                    "Projected Remaining": (
                        format_currency(int(item["projected_remaining_expense"]))
                        if item["projected_remaining_expense"] is not None
                        else "N/A"
                    ),
                    "Included in Global Outlook": item[
                        "included_in_global_outlook"
                    ],
                    "Exclusion Reason": item["global_exclusion_reason"] or "",
                }
            )
        st.dataframe(
            pd.DataFrame(category_rows),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("**Global Outlook calculation**")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Metric": "Normalized Spending So Far",
                        "Value": format_currency(
                            int(spending_limit_status["normalized_monthly_spending_so_far"])
                        ),
                    },
                    {
                        "Metric": "Global Projected Remaining Spending",
                        "Value": format_currency(
                            int(outlook["global_projected_remaining_spending"])
                        ),
                    },
                    {
                        "Metric": "Projected Normalized Monthly Spending",
                        "Value": format_currency(
                            int(
                                spending_limit_status[
                                    "projected_normalized_monthly_spending"
                                ]
                            )
                        ),
                    },
                    {
                        "Metric": "Monthly Spending Limit",
                        "Value": (
                            format_currency(
                                int(spending_limit_status["monthly_spending_limit"])
                            )
                            if bool(spending_limit_status["configured"])
                            else "Not configured"
                        ),
                    },
                    {
                        "Metric": "Spending Limit Gap",
                        "Value": format_currency(
                            int(spending_limit_status["spending_limit_gap"])
                        ),
                    },
                    {
                        "Metric": "Current Balance",
                        "Value": format_currency(int(outlook["current_balance"])),
                    },
                    {
                        "Metric": "Global Estimated Balance",
                        "Value": format_currency(
                            int(outlook["global_estimated_balance"])
                        ),
                    },
                    {
                        "Metric": "Spending Risk",
                        "Value": str(bool(spending_limit_status["spending_risk"])),
                    },
                    {
                        "Metric": "Balance Risk",
                        "Value": str(bool(outlook["balance_risk"])),
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


def render_selected_expense_forecasts(
    forecasts: Sequence[Mapping[str, object]],
) -> None:
    """Render selected category forecast cards and confidence warnings."""

    if not forecasts:
        st.info("Pilih satu atau lebih kategori untuk melihat forecast.")
        return
    for forecast in forecasts:
        with st.container(border=True):
            st.markdown(f"**{forecast['category']}**")
            if forecast["forecast_data_quality"] == "limited":
                st.warning(
                    "Limited historical data — forecast may be less reliable.",
                    icon="⚠️",
                )
            first, second, third = st.columns(3)
            first.metric(
                "Average Daily Spending",
                format_currency(float(forecast["average_daily_spending"])),
            )
            second.metric(
                "Spent So Far This Month",
                format_currency(int(forecast["spent_so_far_this_month"])),
            )
            third.metric(
                "Projected Remaining Expense",
                format_currency(int(forecast["projected_remaining_expense"])),
            )
            st.metric(
                "Estimated Month Total",
                format_currency(int(forecast["estimated_month_total"])),
            )
            st.caption(
                "Historical window: "
                f"{forecast['historical_window_days']} days · "
                f"{forecast['transaction_count']} transactions · "
                f"{forecast['active_days']} active days"
            )


def render_forecast_data_notes(
    limited_categories: Sequence[Mapping[str, object]],
    insufficient_categories: Sequence[Mapping[str, object]],
) -> None:
    """Explain limited and insufficient Forecast data without hard exclusion wording."""

    if not limited_categories and not insufficient_categories:
        return
    with st.expander("Limited Forecast Data", expanded=False):
        for category in limited_categories:
            reasons = "; ".join(category["limited_forecast_reasons"])
            st.caption(
                f"**{category['category']}** — {reasons}. "
                "A basic forecast remains available with a confidence warning."
            )
        for category in insufficient_categories:
            reasons = "; ".join(category["ineligibility_reasons"])
            st.caption(
                f"**{category['category']}** — insufficient data for a safe basic forecast: {reasons}."
            )


def render_goal_forecast(result: Mapping[str, object]) -> None:
    """Render Goal V2 forecasts without calculating financial values in UI."""

    st.subheader("Goal Forecast")
    goals = result["goals"]
    if not goals:
        st.info("No active or paused Goals to forecast.")
        st.caption("Create an Account-linked Goal in Profile to enable this section.")
        return
    for summary in goals:
        _render_goal_card(summary)


def _render_goal_card(summary: Mapping[str, object]) -> None:
    """Render one service-derived Goal V2 forecast card."""

    goal = summary["goal"]
    account = summary["account"]
    if not isinstance(goal, Goal):
        return
    with st.container(border=True):
        title = (
            f"{account.account_name} — {account.account_location}"
            if isinstance(account, Account)
            else "Historical Goal"
        )
        st.markdown(f"**{title}**")
        current = summary["current_progress"]
        remaining = summary["remaining_amount"]
        if isinstance(current, int) and isinstance(remaining, int):
            first, second, third = st.columns(3)
            first.metric("Target", format_currency(goal.target_amount))
            second.metric("Current Progress", format_currency(current))
            third.metric("Remaining", format_currency(remaining))
        required = summary["required_monthly_contribution"]
        pace = summary["contribution_pace"]
        fourth, fifth, sixth = st.columns(3)
        fourth.metric(
            "Required Monthly Contribution",
            format_currency(float(required)) if isinstance(required, (int, float)) else "N/A",
        )
        pace_amount = pace["monthly_amount"]
        fifth.metric(
            "Actual Monthly Contribution Pace",
            format_currency(float(pace_amount)) if isinstance(pace_amount, (int, float)) else "N/A",
        )
        sixth.metric("Projected Completion", str(summary["projected_completion_label"]))
        st.caption(
            f"Status: {goal.status.title()} · Health: {summary['health']} · "
            f"Deadline: {_deadline_label(goal.deadline)}"
        )


def _deadline_label(deadline: str | None) -> str:
    """Return a compact optional deadline label."""

    return deadline or "No deadline"
