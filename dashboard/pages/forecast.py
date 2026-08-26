"""Forecast V2 page for selected expense categories and Account-linked Goals."""

from __future__ import annotations

import streamlit as st

from dashboard.components.forecast_v2 import (
    render_financial_outlook,
    render_forecast_data_notes,
    render_goal_forecast,
    render_selected_expense_forecasts,
)
from dashboard.components.recommendation_v1 import render_recommendations
from dashboard.components.saving_candidates import render_saving_candidate_form
from dashboard.components.scenario_simulator import render_scenario_simulator
from services.category_definitions import EXPENSE_CATEGORIES
from services.forecast_service import ForecastService
from services.recommendation_service import RecommendationService
from services.settings_service import SettingsService


def render() -> None:
    """Render Forecast V2 through ForecastService without direct Sheets access."""

    st.title("Forecast")
    service = ForecastService()
    try:
        with st.spinner("Loading expense forecast..."):
            expense_forecast = service.get_expense_forecast()
    except Exception:
        st.error("Unable to load expense forecast. Please try again.")
        st.caption("Check the Google Sheets connection and try Refresh.")
        return

    try:
        with st.spinner("Calculating global Financial Outlook..."):
            outlook = service.get_financial_outlook(expense_forecast=expense_forecast)
    except Exception:
        st.error("Unable to calculate Financial Outlook.")
        return

    spending_limit_status = service.get_monthly_spending_limit_status(
        monthly_spending_limit=SettingsService().get_monthly_spending_limit(),
        expense_forecast=expense_forecast,
        financial_outlook=outlook,
    )
    outlook = {**outlook, "monthly_spending_limit_status": spending_limit_status}
    render_financial_outlook(outlook, spending_limit_status, expense_forecast)

    _render_expense_forecast_detail(expense_forecast)
    goal_forecast = _render_goal_forecast(service)
    saving_candidates = _render_saving_candidate_preferences(expense_forecast)
    _render_recommendation(
        outlook,
        expense_forecast,
        goal_forecast,
        saving_candidates,
        spending_limit_status,
    )
    render_scenario_simulator(outlook, goal_forecast)


def _render_expense_forecast_detail(
    expense_forecast: dict[str, object],
) -> None:
    """Render inspection-only category details from precomputed Forecast data."""

    forecastable_categories = expense_forecast["forecastable_categories"]
    labels = [str(item["category"]) for item in forecastable_categories]
    st.subheader("Expense Forecast Detail")
    if not labels:
        st.info("No expense category has enough data for a safe basic forecast.")
        render_forecast_data_notes(
            expense_forecast["limited_forecast_categories"],
            expense_forecast["insufficient_forecast_categories"],
        )
        return

    st.caption(
        "Categories to inspect control only the detail cards below. They do not "
        "change Financial Outlook, risk, Recommendation, or Scenario baseline."
    )
    _render_forecast_category_groups(expense_forecast)
    selected_categories = st.multiselect(
        "Categories to inspect",
        options=labels,
        default=_valid_selected_categories(labels),
        key="forecast_selected_categories",
        help="This selection is presentation-only; global calculations remain unchanged.",
    )
    forecasts_by_category = {
        str(item["category"]): item for item in forecastable_categories
    }
    render_selected_expense_forecasts(
        [forecasts_by_category[category] for category in selected_categories]
    )
    render_forecast_data_notes(
        expense_forecast["limited_forecast_categories"],
        expense_forecast["insufficient_forecast_categories"],
    )


def _render_goal_forecast(service: ForecastService) -> dict[str, object]:
    """Render Account-linked Goal Forecast V2 results from the service layer."""

    try:
        with st.spinner("Loading Goal Forecast..."):
            result = service.get_goal_forecast()
    except Exception:
        st.error("Unable to load Goal Forecast. Please try again.")
        return {"goals": []}
    render_goal_forecast(result)
    return result


def _render_saving_candidate_preferences(
    expense_forecast: dict[str, object],
) -> dict[str, bool]:
    """Render and persist the explicit user-owned Saving Candidate preference."""

    settings_service = SettingsService()
    categories = _saving_candidate_categories(expense_forecast)
    category_names = [str(item["category"]) for item in categories]
    preferences = settings_service.get_saving_candidates(category_names)
    submitted = render_saving_candidate_form(categories, preferences)
    if submitted is None:
        return preferences
    try:
        saved = settings_service.save_saving_candidates(submitted)
    except (OSError, ValueError):
        st.error("Unable to save Saving Candidate preferences. Please try again.")
        return preferences
    st.success("Saving Candidate preferences saved.")
    return saved


def _saving_candidate_categories(
    expense_forecast: dict[str, object],
) -> list[dict[str, object]]:
    """Return V1 Expense Categories plus discovered legacy categories."""

    category_data = {
        str(item["category"]): dict(item)
        for item in expense_forecast["categories"]
    }
    categories = [
        category_data.get(
            name,
            {
                "category": name,
                "forecast_data_quality": "no_data",
                "optimization_history_sufficient": False,
            },
        )
        for name in EXPENSE_CATEGORIES
    ]
    dynamic_names = sorted(
        name for name in category_data if name not in EXPENSE_CATEGORIES
    )
    categories.extend(category_data[name] for name in dynamic_names)
    return categories


def _render_forecast_category_groups(
    expense_forecast: dict[str, object],
) -> None:
    """Show sufficient and limited Forecast data groups before selection."""

    sufficient = [
        str(item["category"])
        for item in expense_forecast["eligible_categories"]
    ]
    limited = [
        str(item["category"])
        for item in expense_forecast["limited_forecast_categories"]
    ]
    if sufficient:
        st.caption(f"Sufficient Data: {', '.join(sufficient)}")
    if limited:
        st.caption(f"Limited Forecast Data: {', '.join(limited)}")


def _render_recommendation(
    financial_outlook: dict[str, object],
    expense_forecast: dict[str, object],
    goal_forecast: dict[str, object],
    saving_candidates: dict[str, bool],
    spending_limit_status: dict[str, object],
) -> None:
    """Generate non-persistent recommendations from already loaded forecasts."""

    try:
        with st.spinner("Preparing recommendations..."):
            result = RecommendationService().get_recommendations(
                financial_outlook=financial_outlook,
                expense_forecast=expense_forecast,
                goal_forecast=goal_forecast,
                saving_candidates=saving_candidates,
                spending_limit_status=spending_limit_status,
            )
    except Exception:
        st.error("Unable to prepare recommendations. Please try again.")
        return
    if render_recommendations(result):
        st.session_state["forecast_scenario_handoff"] = result["scenario_handoff"]
        st.session_state.pop("scenario_handoff_applied", None)
        st.success("Recommendation inputs are ready in Scenario Simulator below.")


def _valid_selected_categories(eligible_categories: list[str]) -> list[str]:
    """Keep Forecast-owned selection state valid after eligibility changes."""

    selected = st.session_state.get("forecast_selected_categories", [])
    if not isinstance(selected, list):
        return []
    return [category for category in selected if category in eligible_categories]
