"""Presentation-only components for Forecast V2 results."""

from __future__ import annotations

from html import escape
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

    with st.container(border=False, key="forecast-outlook"):
        st.markdown(
            "<div class=\"pf-forecast-section-title\">"
            "<span class=\"material-symbols-rounded\">monitoring</span>"
            "1. Financial Outlook</div>",
            unsafe_allow_html=True,
        )
        _render_outlook_status(outlook, spending_limit_status)

        projected_spending = int(
            spending_limit_status["projected_normalized_monthly_spending"]
        )
        monthly_limit = spending_limit_status.get("monthly_spending_limit")
        spending_gap = int(spending_limit_status.get("spending_limit_gap", 0))
        primary_cards = st.columns(3)
        with primary_cards[0]:
            _render_metric_card(
                (
                    "forecast-outlook-primary-spending-risk"
                    if bool(spending_limit_status.get("spending_risk", False))
                    else "forecast-outlook-primary-spending-neutral"
                ),
                "Projected Normalized Monthly Spending",
                format_currency(projected_spending),
                help_text="Normalized spending in the current month plus usable category forecasts.",
            )
        with primary_cards[1]:
            _render_metric_card(
                "forecast-outlook-primary-limit",
                "Monthly Spending Limit",
                format_currency(int(monthly_limit)) if monthly_limit is not None else "Not configured",
                help_text="Monthly planning limit from Settings.",
            )
        with primary_cards[2]:
            _render_metric_card(
                (
                    "forecast-outlook-primary-gap-risk"
                    if spending_gap > 0
                    else "forecast-outlook-primary-gap-healthy"
                ),
                "Spending Gap",
                format_currency(spending_gap),
                help_text="Amount projected above the configured Monthly Spending Limit.",
            )

        secondary_cards = st.columns(3)
        with secondary_cards[0]:
            _render_metric_card(
                "forecast-outlook-secondary-current",
                "Current Balance",
                format_currency(int(outlook["current_balance"])),
                help_text="Combined derived balance across active Accounts.",
            )
        with secondary_cards[1]:
            _render_metric_card(
                (
                    "forecast-outlook-secondary-estimated-risk"
                    if int(outlook["global_estimated_balance"]) < 0
                    else "forecast-outlook-secondary-estimated-healthy"
                ),
                "Global Estimated Balance",
                format_currency(int(outlook["global_estimated_balance"])),
                help_text="Current Balance minus Global Projected Remaining Spending.",
            )
        with secondary_cards[2]:
            _render_metric_card(
                "forecast-outlook-secondary-remaining",
                "Global Projected Remaining Spending",
                format_currency(int(outlook["global_projected_remaining_spending"])),
                help_text="Usable expense Forecast aggregated across global categories.",
            )
        render_calculation_details(outlook, spending_limit_status, expense_forecast)


def _render_metric_card(
    key: str,
    label: str,
    value: str,
    *,
    help_text: str,
) -> None:
    """Render a visual Forecast metric without changing service data."""

    with st.container(border=False, key=key):
        st.metric(label, value, help=help_text)


def _render_outlook_status(
    outlook: Mapping[str, object],
    spending_limit_status: Mapping[str, object],
) -> None:
    """Render service-derived Spending and Balance risk states."""

    spending_configured = bool(spending_limit_status.get("configured", False))
    spending_risk = bool(spending_limit_status.get("spending_risk", False))
    balance_risk = bool(outlook.get("balance_risk", False))
    if balance_risk and spending_risk:
        st.error(
            "Balance Risk + Spending Risk: projected spending is over the monthly limit and global estimated balance is below zero.",
            icon=":material/warning:",
        )
    elif balance_risk:
        st.error(
            "Balance Risk: global estimated balance is below zero.",
            icon=":material/error:",
        )
    elif spending_configured and spending_risk:
        st.warning(
            "Spending Risk: projected normalized spending exceeds the Monthly Spending Limit.",
            icon=":material/warning:",
        )
    elif spending_configured:
        st.success("Healthy: spending is within the Monthly Spending Limit.", icon=":material/check_circle:")
    else:
        st.info("Monthly Spending Limit has not been configured.", icon=":material/info:")


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
        st.markdown(
            "<div class=\"pf-forecast-empty-note\">"
            "<span class=\"material-symbols-rounded\">insights</span>"
            "Choose one or more categories to inspect their forecast."
            "</div>",
            unsafe_allow_html=True,
        )
        return
    columns = st.columns(min(3, len(forecasts)))
    for index, forecast in enumerate(forecasts):
        with columns[index % len(columns)]:
            with st.container(border=False, key=f"forecast-category-card-{index}"):
                quality = str(forecast["forecast_data_quality"])
                quality_label = (
                    "Sufficient Data" if quality == "sufficient" else "Limited Data"
                )
                st.markdown(
                    "<div class=\"pf-forecast-card-heading\"><strong>"
                    f"{escape(str(forecast['category']))}</strong>"
                    f"<span class=\"pf-forecast-badge pf-forecast-badge--{quality}\">{quality_label}</span></div>",
                    unsafe_allow_html=True,
                )
                first, second = st.columns(2)
                first.metric(
                    "Spent so far",
                    format_currency(int(forecast["spent_so_far_this_month"])),
                )
                second.metric(
                    "Average daily",
                    format_currency(float(forecast["average_daily_spending"])),
                )
                st.metric(
                    "Projected remaining",
                    format_currency(int(forecast["projected_remaining_expense"])),
                )
                st.divider()
                st.metric(
                    "Estimated month total",
                    format_currency(int(forecast["estimated_month_total"])),
                )
                st.caption(
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

    st.markdown(
        "<div class=\"pf-forecast-section-title\">"
        "<span class=\"material-symbols-rounded\">target</span>"
        "3. Goal Forecast</div>",
        unsafe_allow_html=True,
    )
    st.caption("Track goal progress and estimated completion.")
    goals = result["goals"]
    if not goals:
        st.info("No active or paused Goals to forecast.")
        st.caption("Create an Account-linked Goal in Profile to enable this section.")
        return
    columns = st.columns(min(3, len(goals)))
    for index, summary in enumerate(goals):
        with columns[index % len(columns)]:
            _render_goal_card(summary, index)


def _render_goal_card(summary: Mapping[str, object], index: int) -> None:
    """Render one service-derived Goal V2 forecast card."""

    goal = summary["goal"]
    account = summary["account"]
    if not isinstance(goal, Goal):
        return
    with st.container(border=False, key=f"forecast-goal-card-{index}"):
        title = (
            f"{account.account_name} — {account.account_location}"
            if isinstance(account, Account)
            else "Historical Goal"
        )
        st.markdown(f"**{title}**")
        current = summary["current_progress"]
        remaining = summary["remaining_amount"]
        if isinstance(current, int) and isinstance(remaining, int):
            percentage = (
                min(max(current / goal.target_amount, 0), 1)
                if goal.target_amount
                else 0
            )
            st.caption(f"{format_currency(current)} / {format_currency(goal.target_amount)}")
            st.progress(percentage, text=f"{percentage * 100:.1f}%")
            first, second = st.columns(2)
            first.metric("Target", format_currency(goal.target_amount))
            second.metric("Remaining", format_currency(remaining))
        required = summary["required_monthly_contribution"]
        pace = summary["contribution_pace"]
        if isinstance(required, (int, float)) and isinstance(pace["monthly_amount"], (int, float)):
            fourth, fifth = st.columns(2)
            fourth.metric("Required monthly", format_currency(float(required)))
            fifth.metric("Current pace", format_currency(float(pace["monthly_amount"])))
            st.caption(f"Estimated completion: {summary['projected_completion_label']}")
        else:
            st.markdown(
                "<div class=\"pf-forecast-goal-note\">"
                "<span class=\"material-symbols-rounded\">info</span>"
                "Insufficient allocation history for a reliable completion estimate."
                "</div>",
                unsafe_allow_html=True,
            )
        st.caption(
            f"Status: {goal.status.title()} · Health: {summary['health']} · "
            f"Deadline: {_deadline_label(goal.deadline)}"
        )


def _deadline_label(deadline: str | None) -> str:
    """Return a compact optional deadline label."""

    return deadline or "No deadline"
