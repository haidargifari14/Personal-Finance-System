"""Selectable category and drilldown cards for the Analytics page."""

from __future__ import annotations

from html import escape
from typing import Mapping

import pandas as pd
import streamlit as st

from dashboard.components.icons import category_icon, material_icon
from dashboard.utils.formatter import format_currency, format_percent


SELECTED_CATEGORY_KEY = "analytics_selected_category"


def _select_category(category: str) -> None:
    """Store the category selected for the Analytics drilldown."""

    st.session_state[SELECTED_CATEGORY_KEY] = category


def render_category_cards(data: pd.DataFrame) -> str | None:
    """Render the existing Top 3 result as compact selectable ranked rows."""

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
        with st.container(
            border=False,
            key=f"analytics-top-category-{category_data.rank}",
        ):
            rank_column, details_column, bar_column, percentage_column, action_column = (
                st.columns([0.55, 1.55, 3.4, 0.75, 1.1], vertical_alignment="center")
            )
            with rank_column:
                st.markdown(
                    "<div class=\"pf-rank-badge\">"
                    f"<span>{category_data.rank}</span>{material_icon('military_tech')}"
                    "</div>",
                    unsafe_allow_html=True,
                )
            with details_column:
                st.markdown(
                    "<div class=\"pf-category-name\">"
                    "<span class=\"pf-category-name__icon\">{icon}</span>{category}</div>"
                    "<div class=\"pf-category-amount\">{amount}</div>".format(
                        category=escape(str(category_data.category)),
                        icon=category_icon(category_data.category),
                        amount=escape(format_currency(category_data.amount)),
                    ),
                    unsafe_allow_html=True,
                )
            with bar_column:
                st.markdown(
                    "<div class=\"pf-category-bar\">"
                    "<div class=\"pf-category-bar__fill\" style=\"width:{percentage:.2f}%\"></div>"
                    "</div>".format(percentage=max(float(category_data.percentage), 0)),
                    unsafe_allow_html=True,
                )
            with percentage_column:
                st.markdown(
                    f"<div class=\"pf-category-percentage\">{format_percent(category_data.percentage)}</div>",
                    unsafe_allow_html=True,
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


def render_category_summary_cards(summary: Mapping[str, object]) -> None:
    """Render service-provided Category Detail values in visual hierarchy."""

    primary_cards = (
        (
            "Total expense",
            format_currency(int(summary["total_expense"])),
            "total",
            "target",
        ),
        (
            "Contribution",
            format_percent(float(summary["contribution"])),
            "contribution",
            "donut_large",
        ),
    )
    secondary_cards = (
        (
            "Average expense",
            format_currency(int(summary["average_expense"])),
            "average",
            "monitoring",
        ),
        (
            "Highest expense",
            format_currency(int(summary["highest_expense"])),
            "highest",
            "north",
        ),
        ("Transaction count", str(summary["transaction_count"]), "count", "receipt_long"),
    )

    _render_summary_row(primary_cards, "primary")
    _render_summary_row(secondary_cards, "secondary")


def _render_summary_row(
    cards: tuple[tuple[str, str, str, str], ...],
    size: str,
) -> None:
    """Render one visual-only row of Category Detail cards."""

    for column, (title, value, variant, icon) in zip(st.columns(len(cards)), cards):
        with column:
            st.markdown(
                "<div class=\"pf-category-summary pf-category-summary--{size} "
                "pf-category-summary--{variant}\">"
                "<div class=\"pf-category-summary__topline\">"
                "<span class=\"pf-category-summary__icon\">{icon}</span>"
                "<div class=\"pf-category-summary__title\">{title}</div></div>"
                "<div class=\"pf-category-summary__value\">{value}</div>"
                "</div>".format(
                    size=escape(size),
                    variant=escape(variant),
                    title=escape(title),
                    value=escape(value),
                    icon=material_icon(icon),
                ),
                unsafe_allow_html=True,
            )
