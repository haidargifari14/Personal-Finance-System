"""
dashboard/components/metric_cards.py

Reusable KPI metric card component.
"""

import streamlit as st


def metric_card(
    title: str,
    value: str,
    delta: str | None = None,
    help_text: str | None = None,
):
    """
    Render a reusable KPI metric card.

    Parameters
    ----------
    title : str
        Card title.

    value : str
        Main metric value.

    delta : str, optional
        Difference from previous period.

    help_text : str, optional
        Tooltip displayed when hovering over the label.
    """

    st.metric(
        label=title,
        value=value,
        delta=delta,
        help=help_text,
        border=True
    )