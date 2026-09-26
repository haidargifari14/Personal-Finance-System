"""Streamlit presentation for the non-persistent Forecast Scenario Simulator."""

from __future__ import annotations

from html import escape
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

    st.markdown(
        "<div class=\"pf-forecast-section-title\">"
        "<span class=\"material-symbols-rounded\">tune</span>"
        "5. Scenario Simulator"
        "<span class=\"pf-forecast-badge pf-forecast-badge--hypothetical\">Hypothetical</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Explore a hypothetical plan without changing your actual financial data.")
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
    if st.button(
        "Reset Scenario",
        key="scenario_reset",
        icon=":material/restart_alt:",
    ):
        _reset_scenario_state()
        st.rerun()


def _render_spending_adjustments(
    outlook: Mapping[str, object],
    categories: list[str],
) -> list[dict[str, object]]:
    """Collect category-specific amount or percentage reductions in session state."""

    st.markdown(
        "<div class=\"pf-forecast-scenario-step\">1. Spending Adjustments</div>",
        unsafe_allow_html=True,
    )
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
    if not chosen:
        return adjustments

    columns = st.columns(min(3, len(chosen)))
    for index, category in enumerate(chosen):
        forecast = forecast_by_category[category]
        baseline = int(forecast["projected_remaining_expense"])
        with columns[index % len(columns)]:
            with st.container(
                border=False,
                key=f"forecast-scenario-adjustment-{category}",
            ):
                st.markdown(f"**{escape(category)}**")
                st.caption(f"Baseline: {format_currency(baseline)}")
                label = st.selectbox(
                    "Type",
                    options=["Nominal", "Percentage"],
                    key=f"scenario_mode_{category}",
                )
                mode = "amount" if label == "Nominal" else "percentage"
                maximum = baseline if mode == "amount" else 100
                value = st.number_input(
                    "Reduction",
                    min_value=0,
                    max_value=maximum,
                    step=1,
                    key=f"scenario_value_{category}",
                    help="Nominal in Rupiah or a percentage of projected future spending.",
                )
                adjustments.append({"category": category, "mode": mode, "value": value})
    return adjustments


def _render_goal_allocations(
    goal_forecast: Mapping[str, object],
    potential_saving: int,
) -> None:
    """Collect optional hypothetical monthly allocation values for active Goals."""

    st.markdown(
        "<div class=\"pf-forecast-scenario-step\">3. Goal Allocation</div>",
        unsafe_allow_html=True,
    )
    if potential_saving <= 0:
        st.caption("No potential saving is available to allocate.")
        return
    eligible = [
        item for item in goal_forecast.get("goals", [])
        if str(getattr(item["goal"], "status", "")).lower() == "active"
        and item.get("account") is not None
    ]
    if not eligible:
        st.caption("No active Account-linked Goal is available for Scenario allocation.")
        return
    st.caption(f"Total hypothetical allocation cannot exceed {format_currency(potential_saving)}.")
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
    for index, goal_id in enumerate(chosen):
        with st.container(
            border=False,
            key=f"forecast-scenario-goal-allocation-{index}",
        ):
            st.caption(labels[goal_id])
            st.number_input(
                "Monthly allocation",
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
        categories = escape(", ".join(limited))
        st.markdown(
            "<div class=\"pf-forecast-inline-warning\">"
            "<span class=\"material-symbols-rounded\">warning</span>"
            f"Limited forecast data: {categories} — estimates are less certain."
            "</div>",
            unsafe_allow_html=True,
        )


def _render_spending_and_balance_impact(scenario: Mapping[str, object]) -> None:
    """Render the three primary, user-facing Scenario outcomes."""

    st.markdown(
        "<div class=\"pf-forecast-scenario-step\">2. Baseline vs Scenario</div>",
        unsafe_allow_html=True,
    )
    improvement = int(scenario["balance_improvement"])
    comparison_rows = (
        (
            "Normalized Monthly Spending",
            int(scenario["baseline_projected_normalized_monthly_spending"]),
            int(scenario["scenario_projected_normalized_monthly_spending"]),
            True,
        ),
        (
            "Estimated Balance",
            int(scenario["baseline_estimated_balance"]),
            int(scenario["scenario_estimated_balance"]),
            False,
        ),
        (
            "Spending Gap",
            int(scenario["baseline_spending_limit_gap"]),
            int(scenario["scenario_spending_limit_gap"]),
            True,
        ),
    )
    _render_comparison_table(comparison_rows)
    st.caption(
        "Potential Saving: "
        f"{format_currency(scenario['potential_saving'])} · Unallocated Saving: "
        f"{format_currency(scenario['unallocated_saving'])}"
    )
    if improvement == 0:
        st.caption("Scenario currently matches baseline.")
    with st.expander("View calculation details"):
        if bool(scenario["monthly_spending_limit_configured"]):
            baseline_status = (
                "Spending Risk" if scenario["baseline_spending_risk"] else "Within Limit"
            )
            scenario_status = (
                "Spending Risk" if scenario["scenario_spending_risk"] else "Within Limit"
            )
            st.caption(
                "Monthly Spending Limit: "
                f"{baseline_status} → {scenario_status} · "
                f"gap {format_currency(scenario['baseline_spending_limit_gap'])} → "
                f"{format_currency(scenario['scenario_spending_limit_gap'])}."
            )
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


def _render_comparison_table(
    rows: tuple[tuple[str, int, int, bool], ...],
) -> None:
    """Render existing Scenario values with presentation-only semantic changes."""

    rendered_rows = []
    for metric, baseline, scenario_value, lower_is_better in rows:
        change_text, change_tone = _scenario_change_label(
            baseline,
            scenario_value,
            lower_is_better=lower_is_better,
        )
        rendered_rows.append(
            "<tr>"
            f"<td>{escape(metric)}</td>"
            f"<td>{format_currency(baseline)}</td>"
            f"<td>{format_currency(scenario_value)}</td>"
            f"<td class=\"pf-scenario-change--{change_tone}\">{change_text}</td>"
            "</tr>"
        )
    st.markdown(
        "<table class=\"pf-scenario-comparison\"><thead><tr>"
        "<th>Metric</th><th>Baseline</th><th>Scenario</th><th>Change</th>"
        "</tr></thead><tbody>"
        f"{''.join(rendered_rows)}</tbody></table>",
        unsafe_allow_html=True,
    )


def _scenario_change_label(
    baseline: int,
    scenario_value: int,
    *,
    lower_is_better: bool,
) -> tuple[str, str]:
    """Format a display-only Scenario delta using existing calculated values."""

    difference = scenario_value - baseline
    if difference == 0:
        return "—", "neutral"
    improved = difference < 0 if lower_is_better else difference > 0
    arrow = "↓" if difference < 0 else "↑"
    amount = format_currency(abs(difference))
    percentage = f" ({difference / baseline:+.1%})" if baseline else ""
    return f"{arrow} {amount}{percentage}", "positive" if improved else "negative"


def _render_trajectory(scenario: Mapping[str, object]) -> None:
    """Render the two-line comparison from service-derived trajectory data."""

    st.markdown(
        "<div class=\"pf-forecast-scenario-step\">4. Balance Trajectory</div>",
        unsafe_allow_html=True,
    )
    scenario_balance_trajectory_chart(
        pd.DataFrame(scenario["baseline_trajectory"]),
        pd.DataFrame(scenario["scenario_trajectory"]),
    )


def _render_goal_impacts(scenario: Mapping[str, object]) -> None:
    """Render only Goals receiving a hypothetical allocation."""

    st.markdown(
        "<div class=\"pf-forecast-scenario-step\">5. Goal Impact</div>",
        unsafe_allow_html=True,
    )
    impacts = scenario["goal_impacts"]
    if not impacts:
        st.caption("Allocate potential saving to an active Goal to see its impact.")
        return
    for index, impact in enumerate(impacts):
        goal = impact["goal"]
        account = impact["account"]
        with st.container(border=False, key=f"forecast-scenario-goal-impact-{index}"):
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
            health, completion = st.columns(2)
            with health:
                st.caption("Health")
                st.markdown(
                    f"{impact['baseline_health']} → **{impact['scenario_health']}**"
                )
            with completion:
                st.caption("Projected Completion")
                st.markdown(
                    f"{impact['baseline_completion']} → "
                    f"**{impact['scenario_completion']}**"
                )
            if impact["allocation"]:
                st.caption(
                    "Hypothetical allocation only; it does not change actual data."
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
