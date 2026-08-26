"""Reusable visual components for Forecast risk detection results."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_risk_cards(result: dict[str, Any]) -> None:
    """Render risk cards, empty state, or insufficient-data state."""

    st.subheader("Risk Detection")
    if result["status"] == "insufficient_data":
        st.info("Unable to evaluate financial risks. More historical transactions are required.")
        return

    risks = result["risks"]
    if not risks:
        st.success("No Financial Risks Detected")
        st.caption("Your current financial projection looks healthy.")
        return

    for risk in risks:
        _render_risk_card(risk)


def _render_risk_card(risk: dict[str, str]) -> None:
    """Render one service-provided risk without deriving its severity."""

    with st.container(border=True):
        st.markdown(f"**{risk['title']}**")
        st.write(risk["description"])
        if risk.get("related_metric"):
            st.caption(risk["related_metric"])
        st.markdown(f"Severity: **{risk['severity']}**")
