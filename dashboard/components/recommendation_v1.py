"""Presentation-only components for deterministic Recommendation Engine V1."""

from __future__ import annotations

from html import escape
from typing import Mapping, Sequence

import streamlit as st

from dashboard.utils.formatter import format_currency


def render_recommendations(result: Mapping[str, object]) -> bool:
    """Render explainable recommendations and return a Try Scenario request."""

    st.markdown(
        "<div class=\"pf-forecast-section-title\">"
        "<span class=\"material-symbols-rounded\">lightbulb</span>"
        "4. Recommendation</div>",
        unsafe_allow_html=True,
    )
    st.caption("Spending insights and saving opportunities.")
    _render_recommendation_message(result)

    potential_saving = int(result["potential_saving"])
    spending_gap = int(result["spending_limit_gap"])
    remaining_gap = int(result["remaining_spending_limit_gap"])
    first, second, third, fourth = st.columns(4)
    with first:
        _render_recommendation_metric(
            (
                "forecast-recommendation-saving-positive"
                if potential_saving > 0
                else "forecast-recommendation-saving-neutral"
            ),
            "Potential Saving",
            format_currency(potential_saving),
        )
    with second:
        _render_recommendation_metric(
            (
                "forecast-recommendation-gap-risk"
                if spending_gap > 0
                else "forecast-recommendation-gap-healthy"
            ),
            "Spending Gap",
            format_currency(spending_gap),
        )
    with third:
        _render_recommendation_metric(
            (
                "forecast-recommendation-remaining-gap-risk"
                if remaining_gap > 0
                else "forecast-recommendation-remaining-gap-healthy"
            ),
            "Remaining Gap",
            format_currency(remaining_gap),
        )
    with fourth:
        _render_recommendation_metric(
            "forecast-recommendation-candidates",
            "Candidates Analyzed",
            str(len(result["candidate_analysis"])),
        )

    _render_expected_impact(result)
    with st.expander("Candidate Details", expanded=False):
        _render_candidate_analysis(result["candidate_analysis"])
        _render_category_recommendations(result["category_recommendations"])
        _render_goal_recommendations(result["goal_recommendations"])
    if not result["category_recommendations"] and not result["goal_recommendations"]:
        return False
    return st.button(
        "Try Scenario",
        key="forecast_try_recommendation_scenario",
        icon=":material/tune:",
        type="primary",
    )


def _render_recommendation_message(result: Mapping[str, object]) -> None:
    """Render the single service-owned recommendation conclusion warmly."""

    potential_saving = int(result["potential_saving"])
    spending_gap = int(result["spending_limit_gap"])
    if potential_saving > 0:
        tone = "positive"
    elif spending_gap > 0:
        tone = "warning"
    else:
        tone = "neutral"
    message = escape(str(result["message"]))
    st.markdown(
        "<div class=\"pf-forecast-recommendation-message "
        f"pf-forecast-recommendation-message--{tone}\">"
        "<span class=\"material-symbols-rounded\">lightbulb</span>"
        f"<span>{message}</span></div>",
        unsafe_allow_html=True,
    )


def _render_recommendation_metric(key: str, label: str, value: str) -> None:
    """Render one visually semantic Recommendation metric."""

    with st.container(border=False, key=key):
        st.metric(label, value)


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
    for index, candidate in enumerate(candidates):
        presentation = _baseline_presentation(
            candidate.get("optimization_baseline_type")
        )
        with st.container(border=True):
            _render_candidate_heading(candidate, presentation)
            if candidate["analysis_status"] != "ready":
                reasons = "; ".join(candidate["optimization_history_reasons"])
                st.markdown(
                    "<div class=\"pf-recommendation-baseline-helper\">"
                    "Not enough spending history to estimate a reliable saving "
                    "opportunity."
                    "</div>",
                    unsafe_allow_html=True,
                )
                if reasons:
                    st.caption(reasons)
                continue
            first, second, third = st.columns(3)
            first.metric(
                presentation["current_label"],
                format_currency(int(candidate["current_comparable_spending"])),
            )
            second.metric(
                presentation["baseline_label"],
                format_currency(
                    int(candidate["historical_normal_comparable_spending"])
                ),
            )
            capacity = int(candidate["saving_capacity"])
            with third:
                tone = "positive" if capacity > 0 else "neutral"
                with st.container(
                    border=False,
                    key=f"forecast-candidate-saving-{tone}-{index}",
                ):
                    st.metric("Potential Saving", format_currency(capacity))
            st.markdown(
                "<div class=\"pf-recommendation-baseline-helper\">"
                f"{presentation['helper']}"
                "</div>",
                unsafe_allow_html=True,
            )
            if capacity > 0:
                st.caption(
                    f"Potential saving: {format_currency(capacity)} over "
                    f"{candidate['comparison_days']} comparable calendar days."
                )
            else:
                st.caption("No reduction opportunity detected for this period.")


def _render_candidate_heading(
    candidate: Mapping[str, object],
    presentation: Mapping[str, str],
) -> None:
    """Render a category name with its user-facing baseline status."""

    category = escape(str(candidate["category"]))
    st.markdown(
        "<div class=\"pf-recommendation-candidate-heading\">"
        f"<strong>{category}</strong>"
        f"<span class=\"pf-baseline-badge {presentation['badge_class']}\" "
        f"title=\"{escape(presentation['tooltip'])}\">"
        f"{presentation['badge_label']}"
        "</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def _baseline_presentation(baseline_type: object) -> dict[str, str]:
    """Return presentation-only copy for one service-owned baseline type."""

    if baseline_type == "historical":
        return {
            "badge_label": "Historical Baseline",
            "badge_class": "pf-baseline-badge--historical",
            "tooltip": "Uses regular spending history from before the current period.",
            "current_label": "Current Regular Spending",
            "baseline_label": "Typical Historical Spending",
            "helper": "Historical data is available and used as the comparison baseline.",
        }
    if baseline_type == "limited_current_period":
        return {
            "badge_label": "Limited Baseline",
            "badge_class": "pf-baseline-badge--limited",
            "tooltip": (
                "Historical data is unavailable, so recent spending is compared "
                "with the earlier part of the current period."
            ),
            "current_label": "Recent Regular Spending",
            "baseline_label": "Early-Period Baseline",
            "helper": (
                "Historical data is not available yet. The comparison uses spending "
                "pace from the earlier part of the current period."
            ),
        }
    return {
        "badge_label": "Insufficient Data",
        "badge_class": "pf-baseline-badge--insufficient",
        "tooltip": "Not enough data is available for a reliable comparison.",
        "current_label": "",
        "baseline_label": "",
        "helper": "Not enough data is available for a reliable comparison.",
    }


def _render_category_recommendations(
    recommendations: Sequence[Mapping[str, object]],
) -> None:
    """Render service-provided bounded category reductions."""

    if not recommendations:
        return
    st.markdown("**Suggested category reductions**")
    for item in recommendations:
        presentation = _baseline_presentation(
            item.get("optimization_baseline_type")
        )
        with st.container(border=True):
            _render_candidate_heading(item, presentation)
            first, second, third = st.columns(3)
            first.metric(
                presentation["current_label"],
                format_currency(int(item["current_comparable_spending"])),
            )
            second.metric(
                presentation["baseline_label"],
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
