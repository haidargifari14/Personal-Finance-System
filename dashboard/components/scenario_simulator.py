"""Streamlit presentation for the non-persistent Forecast Scenario Simulator."""

from __future__ import annotations

from typing import Mapping

import pandas as pd
import streamlit as st

from dashboard.components.charts import scenario_balance_trajectory_chart
from dashboard.utils.formatter import format_currency
from services.scenario_service import ScenarioService


SCENARIO_STATE_PREFIX = "scenario_"


def render_scenario_simulator(
    outlook: Mapping[str, object],
    goal_forecast: Mapping[str, object],
) -> None:
    """Render an editable, session-only Scenario from already loaded results."""

    st.subheader("Scenario Simulator")
    st.caption(
        "Scenario adalah sandbox hipotetis. Perubahan di sini tidak menyimpan "
        "Transaction, Account, Account Movement, atau Goal."
    )
    _apply_recommendation_handoff(outlook)
    forecastable_categories = [
        str(item["category"])
        for item in outlook.get(
            "global_forecast_categories",
            outlook.get("selected_categories", []),
        )
    ]
    if not forecastable_categories:
        st.info("No globally forecastable category is available for Scenario.")
        return

    adjustments = _render_spending_adjustments(outlook, forecastable_categories)
    allocations = _current_goal_allocations()
    try:
        scenario = ScenarioService().simulate(
            outlook=outlook,
            goal_forecast=goal_forecast,
            adjustments=adjustments,
            goal_allocations=allocations,
        )
    except ValueError as error:
        scenario = ScenarioService().simulate(
            outlook=outlook,
            goal_forecast=goal_forecast,
            adjustments=adjustments,
        )
        allocation_error = str(error)
    else:
        allocation_error = None

    _render_limited_data_warning(scenario)
    _render_spending_and_balance_impact(scenario)
    _render_goal_allocations(goal_forecast, scenario["potential_saving"])
    if allocation_error:
        st.error(allocation_error)
    _render_trajectory(scenario)
    _render_goal_impacts(scenario)
    if st.button("Reset Scenario", key="scenario_reset"):
        _reset_scenario_state()
        st.rerun()


def _render_spending_adjustments(
    outlook: Mapping[str, object],
    categories: list[str],
) -> list[dict[str, object]]:
    """Collect category-specific amount or percentage reductions in session state."""

    st.markdown("#### 1. Spending Adjustments")
    chosen = st.multiselect(
        "Categories to adjust",
        options=categories,
        key="scenario_adjusted_categories",
        help="Only categories with a usable Forecast projection can be simulated.",
    )
    forecast_by_category = {
        str(item["category"]): item
        for item in outlook.get(
            "global_forecast_categories",
            outlook.get("selected_categories", []),
        )
    }
    adjustments = []
    for category in chosen:
        forecast = forecast_by_category[category]
        baseline = int(forecast["projected_remaining_expense"])
        with st.container(border=True):
            st.markdown(f"**{category}** — Baseline future expense: {format_currency(baseline)}")
            first, second = st.columns(2)
            with first:
                label = st.selectbox(
                    "Reduction type",
                    options=["Nominal", "Percentage"],
                    key=f"scenario_mode_{category}",
                )
            mode = "amount" if label == "Nominal" else "percentage"
            with second:
                maximum = baseline if mode == "amount" else 100
                value = st.number_input(
                    "Reduction value",
                    min_value=0,
                    max_value=maximum,
                    step=1,
                    key=f"scenario_value_{category}",
                    help="Nominal dalam Rupiah atau persentase dari proyeksi biaya masa depan.",
                )
            adjustments.append({"category": category, "mode": mode, "value": value})
    return adjustments


def _render_goal_allocations(
    goal_forecast: Mapping[str, object],
    potential_saving: int,
) -> None:
    """Collect optional hypothetical monthly allocation values for active Goals."""

    st.markdown("#### 3. Goal Allocation")
    eligible = [
        item for item in goal_forecast.get("goals", [])
        if str(getattr(item["goal"], "status", "")).lower() == "active"
        and item.get("account") is not None
    ]
    if not eligible:
        st.info("Belum ada Goal aktif dengan Account yang tersedia untuk Scenario.")
        return
    st.caption(
        "Total hypothetical allocation cannot exceed "
        f"{format_currency(potential_saving)}."
    )
    labels = {
        str(item["goal"].goal_id): (
            f"{item['account'].account_name} — {item['goal'].priority.title()} priority"
        )
        for item in eligible
    }
    chosen = st.multiselect(
        "Goals to allocate hypothetical saving",
        options=list(labels),
        format_func=labels.get,
        key="scenario_allocated_goals",
    )
    for goal_id in chosen:
        st.number_input(
            f"Monthly Scenario allocation: {labels[goal_id]}",
            min_value=0,
            step=1,
            key=f"scenario_goal_allocation_{goal_id}",
        )


def _current_goal_allocations() -> dict[str, int]:
    """Read the persisted-in-session Goal allocation widgets before rendering."""

    goal_ids = st.session_state.get("scenario_allocated_goals", [])
    if not isinstance(goal_ids, list):
        return {}
    return {
        str(goal_id): int(st.session_state.get(f"scenario_goal_allocation_{goal_id}", 0))
        for goal_id in goal_ids
    }


def _render_limited_data_warning(scenario: Mapping[str, object]) -> None:
    """Keep low-confidence Forecast use visible without blocking Scenario use."""

    limited = [
        str(item["category"])
        for item in scenario["category_impacts"]
        if item["forecast_data_quality"] == "limited"
    ]
    if limited:
        st.warning(
            "Scenario ini mencakup Limited Forecast Data untuk: "
            f"{', '.join(limited)}. Pengeluaran aktual dapat berbeda material."
        )


def _render_spending_and_balance_impact(scenario: Mapping[str, object]) -> None:
    """Render the three primary, user-facing Scenario outcomes."""

    st.markdown("#### 2. Global Outlook Comparison")
    first, second, third, fourth = st.columns(4)
    improvement = int(scenario["balance_improvement"])
    percentage = scenario["balance_improvement_percentage"]
    if improvement > 0:
        indicator = "↑"
        delta = f"{float(percentage):+.1f}%" if percentage is not None else "Baseline is zero"
        delta_color = "normal"
    elif improvement < 0:
        indicator = "↓"
        delta = f"{float(percentage):+.1f}%" if percentage is not None else "Baseline is zero"
        delta_color = "normal"
    else:
        indicator = "→"
        delta = "0.0%" if percentage is not None else "Baseline is zero"
        delta_color = "off"
    first.metric(
        "Balance Improvement",
        f"{indicator} {format_currency(improvement)}",
        delta=delta,
        delta_color=delta_color,
    )
    second.metric(
        "Scenario Estimated Balance",
        format_currency(scenario["scenario_estimated_balance"]),
    )
    third.metric(
        "Scenario Normalized Spending",
        format_currency(scenario["scenario_projected_normalized_monthly_spending"]),
    )
    fourth.metric("Unallocated Saving", format_currency(scenario["unallocated_saving"]))
    if bool(scenario["monthly_spending_limit_configured"]):
        baseline_status = "Spending Risk" if scenario["baseline_spending_risk"] else "Within Limit"
        scenario_status = "Spending Risk" if scenario["scenario_spending_risk"] else "Within Limit"
        st.caption(
            "Monthly Spending Limit: "
            f"{baseline_status} → {scenario_status} · "
            f"gap {format_currency(scenario['baseline_spending_limit_gap'])} → "
            f"{format_currency(scenario['scenario_spending_limit_gap'])}."
        )
    st.caption(
        "Goal Allocation is hypothetical monthly planning only; it is not a "
        "Transaction, Transfer, Account Movement, or Account balance update."
    )
    with st.expander("View calculation details"):
        st.write(
            {
                "Current Balance": format_currency(scenario["current_balance"]),
                "Baseline Projected Remaining Spending": format_currency(
                    scenario["baseline_projected_remaining_spending"]
                ),
                "Scenario Projected Remaining Spending": format_currency(
                    scenario["scenario_projected_remaining_spending"]
                ),
                "Baseline Projected Normalized Monthly Spending": format_currency(
                    scenario["baseline_projected_normalized_monthly_spending"]
                ),
                "Scenario Projected Normalized Monthly Spending": format_currency(
                    scenario["scenario_projected_normalized_monthly_spending"]
                ),
                "Baseline Estimated Balance": format_currency(
                    scenario["baseline_estimated_balance"]
                ),
                "Total Potential Saving": format_currency(scenario["potential_saving"]),
                "Goal Allocation": format_currency(scenario["total_goal_allocation"]),
                "Unallocated Saving": format_currency(scenario["unallocated_saving"]),
            }
        )


def _render_trajectory(scenario: Mapping[str, object]) -> None:
    """Render the two-line comparison from service-derived trajectory data."""

    st.markdown("#### 4. Balance Trajectory")
    scenario_balance_trajectory_chart(
        pd.DataFrame(scenario["baseline_trajectory"]),
        pd.DataFrame(scenario["scenario_trajectory"]),
    )


def _render_goal_impacts(scenario: Mapping[str, object]) -> None:
    """Render only Goals receiving a hypothetical allocation."""

    st.markdown("#### 5. Goal Impact")
    impacts = scenario["goal_impacts"]
    if not impacts:
        st.info("Alokasikan Potential Saving ke Goal aktif untuk melihat dampaknya.")
        return
    st.caption(
        "Projected Goal Completion assumes the simulated monthly allocation "
        "continues in future months."
    )
    for impact in impacts:
        goal = impact["goal"]
        account = impact["account"]
        with st.container(border=True):
            st.markdown(
                f"**{account.account_name} — {goal.priority.title()} priority Goal**"
            )
            first, second, third = st.columns(3)
            first.metric("Scenario Allocation", format_currency(impact["allocation"]))
            second.metric(
                "Contribution Pace",
                format_currency(impact["scenario_monthly_pace"]),
                delta=(
                    f"+{format_currency(impact['allocation'])}/month"
                    if impact["allocation"] else None
                ),
            )
            third.metric(
                "Simulated Goal Position",
                format_currency(impact["simulated_current_progress"]),
            )
            st.write(
                f"Health: **{impact['baseline_health']} → {impact['scenario_health']}**  \\n"
                f"Projected completion: **{impact['baseline_completion']} → "
                f"{impact['scenario_completion']}**"
            )
            if impact["remaining_contribution_gap"]:
                st.caption(
                    "Remaining monthly contribution gap: "
                    f"{format_currency(impact['remaining_contribution_gap'])}"
                )


def _apply_recommendation_handoff(outlook: Mapping[str, object]) -> None:
    """Consume a Recommendation handoff once while keeping it editable afterward."""

    handoff = st.session_state.get("forecast_scenario_handoff")
    if not handoff or st.session_state.get("scenario_handoff_applied"):
        return
    available = {
        str(item["category"]): int(item["projected_remaining_expense"])
        for item in outlook.get(
            "global_forecast_categories",
            outlook.get("selected_categories", []),
        )
    }
    categories = []
    for adjustment in handoff.get("category_adjustments", []):
        category = str(adjustment.get("category") or "")
        if category not in available:
            continue
        categories.append(category)
        st.session_state[f"scenario_mode_{category}"] = "Nominal"
        suggested = int(
            adjustment.get("suggested_reduction", adjustment.get("amount", 0))
        )
        st.session_state[f"scenario_value_{category}"] = min(
            suggested,
            available[category],
        )
        if suggested > available[category]:
            st.session_state["scenario_handoff_notice"] = (
                "Recommendation reduction exceeded the global Forecast baseline "
                f"for {category}, so the editable Scenario prefill uses its maximum."
            )
    st.session_state["scenario_adjusted_categories"] = list(dict.fromkeys(categories))
    goal_ids = []
    for allocation in handoff.get("goal_allocations", []):
        goal_id = str(allocation.get("goal_id") or "")
        if not goal_id:
            continue
        goal_ids.append(goal_id)
        st.session_state[f"scenario_goal_allocation_{goal_id}"] = int(
            allocation.get("amount", 0)
        )
    st.session_state["scenario_allocated_goals"] = list(dict.fromkeys(goal_ids))
    st.session_state["scenario_handoff_applied"] = True
    if categories or goal_ids:
        st.info("Recommendation prefill loaded. You can modify or remove every value.")
    if notice := st.session_state.get("scenario_handoff_notice"):
        st.warning(notice)


def _reset_scenario_state() -> None:
    """Clear only temporary Scenario state; source-of-truth data is untouched."""

    for key in list(st.session_state):
        if key.startswith(SCENARIO_STATE_PREFIX) or key == "forecast_scenario_handoff":
            del st.session_state[key]
