"""Reusable UI for explicit Saving Candidate preferences."""

from __future__ import annotations

from typing import Mapping, Sequence

import streamlit as st


def render_saving_candidate_form(
    categories: Sequence[Mapping[str, object]],
    preferences: Mapping[str, bool],
) -> dict[str, bool] | None:
    """Render independent optimization preferences and return submissions only."""

    with st.expander("Saving Candidate Configuration", expanded=False):
        st.caption(
            "Choose categories that may be analyzed as spending optimization "
            "targets. This is independent from the Forecast display selection."
        )
        with st.form("saving_candidate_form"):
            submitted = {
                str(category["category"]): st.checkbox(
                    _category_label(category),
                    value=bool(preferences.get(str(category["category"]), False)),
                    key=f"forecast_saving_candidate_{category['category']}",
                )
                for category in categories
            }
            save_requested = st.form_submit_button("Save Saving Candidates")
    return submitted if save_requested else None


def _category_label(category: Mapping[str, object]) -> str:
    """Label a candidate with Forecast confidence without coupling the rules."""

    quality = str(category.get("forecast_data_quality", "no_data"))
    if quality == "sufficient":
        confidence = "Forecast Ready"
    elif quality == "limited":
        confidence = "Limited Forecast Data"
    else:
        confidence = "No Forecast Data"
    return f"{category['category']} — {confidence}"
