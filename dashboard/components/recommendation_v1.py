"""Presentation-only components for deterministic Recommendation Engine V1."""

from __future__ import annotations

from typing import Mapping, Sequence

import streamlit as st

from dashboard.utils.formatter import format_currency


def render_recommendations(result: Mapping[str, object]) -> bool:
    """Render explainable recommendations and return a Try Scenario request."""

    st.subheader("Recommendation")
    limit_status = result["spending_limit_status"]
    first, second = st.columns(2)
    first.metric(
        "Saving Candidates Analyzed",
        str(len(result["candidate_analysis"])),
    )
    second.metric(
        "Total Potential Saving",
        format_currency(int(result["potential_saving"])),
    )
    if bool(result["balance_risk"]):
        st.warning(
            "Financial Outlook reports a Balance Risk. The actions below show "
            "whether realistic savings can reduce its gap.",
            icon="⚠️",
        )
    if bool(result["spending_risk"]):
        st.warning(
            "Financial Outlook reports a Spending Risk. Recommendation does not "
            "recalculate that status.",
            icon="⚠️",
        )
    if bool(result["balance_risk"]):
        first, second = st.columns(2)
        first.metric(
            "Balance Shortfall",
            format_currency(int(result["balance_shortfall"])),
        )
        second.metric(
            "Remaining Balance Shortfall",
            format_currency(int(result["remaining_balance_shortfall"])),
        )
    if bool(result["spending_risk"]):
        first, second = st.columns(2)
        first.metric(
            "Spending Limit Gap",
            format_currency(int(result["spending_limit_gap"])),
        )
        second.metric(
            "Remaining Spending Limit Gap",
            format_currency(int(result["remaining_spending_limit_gap"])),
        )
    st.info(str(result["message"]))
    _render_expected_impact(result)
    _render_candidate_analysis(result["candidate_analysis"])
    _render_category_recommendations(result["category_recommendations"])
    _render_goal_recommendations(result["goal_recommendations"])
    if not result["category_recommendations"] and not result["goal_recommendations"]:
        if int(result["potential_saving"]) == 0:
            st.info("No realistic spending optimization opportunity detected.")
        return False
    st.caption(
        "Recommendations are analytical only. They do not create transactions "
        "or change Account, movement, or Goal data."
    )
    return st.button("Try Scenario", key="forecast_try_recommendation_scenario")


def _render_expected_impact(result: Mapping[str, object]) -> None:
    """Explain the service-derived impact without duplicating Financial Outlook."""

    applied_saving = int(result["applied_saving"])
    if applied_saving <= 0:
        return
    st.caption(
        "Expected impact: global estimated balance improves "
        f"by {format_currency(applied_saving)} to "
        f"{format_currency(int(result['expected_estimated_balance_after_recommendation']))}."
    )


def _render_candidate_analysis(
    candidates: Sequence[Mapping[str, object]],
) -> None:
    """Explain every enabled Saving Candidate, including no-opportunity states."""

    st.markdown("**Saving Candidates analyzed**")
    if not candidates:
        st.caption("No Saving Candidate is currently enabled.")
        return
    for candidate in candidates:
        with st.container(border=True):
            st.markdown(f"**{candidate['category']}**")
            if candidate["analysis_status"] != "ready":
                reasons = "; ".join(candidate["optimization_history_reasons"])
                st.caption(
                    "Saving Candidate: ON · Insufficient optimization history. "
                    f"{reasons}"
                )
                continue
            st.caption(
                f"Baseline Type: {_baseline_type_label(candidate['optimization_baseline_type'])}"
            )
            first, second, third = st.columns(3)
            first.metric(
                "Normalized comparable spending",
                format_currency(int(candidate["current_comparable_spending"])),
            )
            second.metric(
                "Historical Normal",
                format_currency(
                    int(candidate["historical_normal_comparable_spending"])
                ),
            )
            third.metric(
                "Detected Excess",
                format_currency(max(int(candidate["optimization_excess"]), 0)),
            )
            capacity = int(candidate["saving_capacity"])
            if capacity > 0:
                st.caption(
                    f"Potential saving: {format_currency(capacity)} over "
                    f"{candidate['comparison_days']} comparable calendar days."
                )
            else:
                st.caption("No reduction opportunity detected for this period.")


def _baseline_type_label(baseline_type: object) -> str:
    """Return a concise explainability label for a service-owned baseline."""

    if baseline_type == "limited_current_period":
        return "Limited Optimization Baseline"
    return "Historical Baseline"


def _render_category_recommendations(
    recommendations: Sequence[Mapping[str, object]],
) -> None:
    """Render service-provided bounded category reductions."""

    if not recommendations:
        return
    st.markdown("**Suggested category reductions**")
    for item in recommendations:
        with st.container(border=True):
            st.markdown(f"**{item['category']}**")
            first, second, third = st.columns(3)
            first.metric(
                "Current Spending",
                format_currency(int(item["current_comparable_spending"])),
            )
            second.metric(
                "Historical Normal",
                format_currency(
                    int(item["historical_normal_comparable_spending"])
                ),
            )
            third.metric(
                "Suggested Reduction",
                format_currency(int(item["suggested_reduction"])),
            )
            details = [
                f"Available saving: {format_currency(int(item['saving_capacity']))}",
            ]
            if int(item["remaining_balance_shortfall"]) > 0:
                details.append(
                    "Remaining balance shortfall: "
                    f"{format_currency(int(item['remaining_balance_shortfall']))}"
                )
            if int(item["remaining_spending_limit_gap"]) > 0:
                details.append(
                    "Remaining Spending Limit gap: "
                    f"{format_currency(int(item['remaining_spending_limit_gap']))}"
                )
            st.caption(" · ".join(details))
            st.write(str(item["explanation"]))


def _render_goal_recommendations(
    recommendations: Sequence[Mapping[str, object]],
) -> None:
    """Render service-provided Goal pace improvements after cashflow allocation."""

    if not recommendations:
        return
    st.markdown("**Suggested Goal contribution improvements**")
    for item in recommendations:
        with st.container(border=True):
            st.markdown(
                f"**Goal {item['goal_id']}** · "
                f"{str(item['goal_priority']).title()} priority"
            )
            first, second, third = st.columns(3)
            first.metric(
                "Contribution Gap",
                format_currency(int(item["contribution_gap"])),
            )
            second.metric(
                "Suggested Allocation",
                format_currency(int(item["suggested_allocation"])),
            )
            third.metric(
                "Remaining Goal Gap",
                format_currency(int(item["remaining_goal_gap"])),
            )
            st.caption(str(item["expected_impact"]))
