"""Selectable category cards for the Personal Finance Dashboard."""

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_percent


SELECTED_CATEGORY_KEY = "analytics_selected_category"
RANK_LABELS = {
    1: "\U0001F947",
    2: "\U0001F948",
    3: "\U0001F949",
}


def _select_category(category: str) -> None:
    """Store the category selected for the Analytics drilldown."""

    st.session_state[SELECTED_CATEGORY_KEY] = category


def render_category_cards(data: pd.DataFrame) -> str | None:
    """Render selectable top-spending category cards and return the selection."""

    if data.empty:
        st.session_state.pop(SELECTED_CATEGORY_KEY, None)
        st.info("Belum ada data pengeluaran untuk filter yang dipilih.")
        return None

    available_categories = data["category"].tolist()
    selected_category = st.session_state.get(SELECTED_CATEGORY_KEY)
    if selected_category not in available_categories:
        selected_category = available_categories[0]
        st.session_state[SELECTED_CATEGORY_KEY] = selected_category

    for category_data in data.itertuples(index=False):
        is_selected = category_data.category == selected_category
        rank_label = RANK_LABELS.get(category_data.rank, f"Top {category_data.rank}")

        with st.container(border=True):
            details_column, action_column = st.columns([5, 1])
            with details_column:
                st.markdown(f"**{rank_label} {category_data.category}**")
                st.caption(
                    f"{format_currency(category_data.amount)} - "
                    f"{format_percent(category_data.percentage)} of total expense"
                )
            with action_column:
                st.button(
                    "Selected" if is_selected else "Select",
                    key=f"select_category_{category_data.category}",
                    width="stretch",
                    type="primary" if is_selected else "secondary",
                    disabled=is_selected,
                    on_click=_select_category,
                    args=(category_data.category,),
                )

    return selected_category
