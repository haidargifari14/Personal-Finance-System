"""Reusable visual components for financial recommendations."""

from __future__ import annotations

import streamlit as st


def render_recommendation_cards(recommendations: list[dict[str, str]]) -> None:
    """Render recommendation cards or an unavailable-state message."""

    st.subheader("AI Recommendation")
    if not recommendations:
        st.info("Recommendations are unavailable until more historical data is available.")
        return
    for recommendation in recommendations:
        with st.container(border=True):
            st.markdown(f"**{recommendation['title']}**")
            st.write(recommendation["reason"])
            st.caption(f"Suggested action: {recommendation['action']}")
            st.caption(f"Expected impact: {recommendation['impact']}")
            st.caption(f"Related: {recommendation['related']} · Priority: {recommendation['priority']}")
