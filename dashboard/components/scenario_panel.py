"""Reusable UI controls for the Forecast scenario simulator."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


SCENARIO_HORIZON_OPTIONS = {
    "30 Days": 30,
    "3 Months": 90,
}


def render_scenario_panel(
    *,
    on_run: Callable[[], None],
    on_reset: Callable[[], None],
) -> None:
    """Render scenario inputs and actions without applying calculations."""

    with st.container(border=True):
        st.subheader("Scenario Simulator")
        st.caption("Test temporary assumptions. Your transactions stay unchanged.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.number_input(
                "Income adjustment (%)",
                min_value=-100.0,
                max_value=100.0,
                step=1.0,
                key="forecast_scenario_income_adjustment",
            )
            st.number_input(
                "Expense adjustment (%)",
                min_value=-100.0,
                max_value=100.0,
                step=1.0,
                key="forecast_scenario_expense_adjustment",
            )
            st.number_input(
                "Additional monthly saving (Rp)",
                min_value=0,
                step=50_000,
                key="forecast_scenario_additional_saving",
            )

        st.segmented_control(
            "Scenario horizon",
            options=SCENARIO_HORIZON_OPTIONS,
            required=True,
            key="forecast_scenario_horizon",
        )
        with st.container(horizontal=True):
            st.button(
                "Run Simulation",
                icon=":material/play_arrow:",
                key="forecast_run_scenario",
                on_click=on_run,
            )
            st.button(
                "Reset Scenario",
                icon=":material/restart_alt:",
                key="forecast_reset_scenario",
                on_click=on_reset,
            )
