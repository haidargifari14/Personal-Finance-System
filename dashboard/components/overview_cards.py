"""Warm-light visual components used only by the Overview page."""

from __future__ import annotations

from html import escape
from typing import Mapping, Sequence

import streamlit as st

from dashboard.utils.formatter import format_currency


_KPI_ICONS = {
    "current": "▣",
    "income": "↓",
    "expense": "↑",
    "cashflow": "⌁",
}


def render_overview_kpi(
    *,
    title: str,
    value: str,
    variant: str,
    metadata: str | None = None,
    is_negative: bool = False,
) -> None:
    """Render one semantically styled Overview KPI card.

    Args:
        title: User-facing metric name.
        value: A service-provided, already formatted metric value.
        variant: Visual semantic variant: current, income, expense, or cashflow.
        metadata: Optional supporting text without financial calculations.
        is_negative: Whether the cashflow metadata should use negative styling.
    """

    metadata_class = ""
    if variant == "income" or (variant == "cashflow" and not is_negative):
        metadata_class = " pf-kpi__meta--positive"
    elif variant == "expense" or (variant == "cashflow" and is_negative):
        metadata_class = " pf-kpi__meta--negative"

    st.markdown(
        "<div class=\"pf-kpi pf-kpi--{variant}\">"
        "<div class=\"pf-kpi__topline\">"
        "<span class=\"pf-kpi__icon\">{icon}</span>{title}</div>"
        "<div class=\"pf-kpi__value\">{value}</div>"
        "{metadata}"
        "</div>".format(
            variant=escape(variant),
            icon=escape(_KPI_ICONS.get(variant, "•")),
            title=escape(title),
            value=escape(value),
            metadata=(
                f"<div class=\"pf-kpi__meta{metadata_class}\">"
                f"{escape(metadata)}</div>"
                if metadata
                else ""
            ),
        ),
        unsafe_allow_html=True,
    )


def render_account_balance_snapshot(
    account_summaries: Sequence[Mapping[str, object]],
) -> None:
    """Render active Accounts with service-calculated balances and comparison bars."""

    active_summaries = [
        summary
        for summary in account_summaries
        if str(summary["account"].status).strip().lower() == "active"
    ]
    if not active_summaries:
        st.info("Belum ada akun aktif untuk ditampilkan.")
        return

    largest_balance = max(
        (abs(int(summary["current_balance"])) for summary in active_summaries),
        default=0,
    )
    st.markdown(
        "<div class=\"pf-section-heading\">"
        "<span class=\"pf-section-heading__title\">▦ Account Balances</span>"
        "<span class=\"pf-section-heading__meta\">Current allocation</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    for summary in active_summaries:
        account = summary["account"]
        balance = int(summary["current_balance"])
        bar_width = 0 if largest_balance == 0 else abs(balance) / largest_balance * 100
        bar_class = " pf-account-row__bar--negative" if balance < 0 else ""
        st.markdown(
            "<div class=\"pf-account-row\">"
            "<div class=\"pf-account-row__line\">"
            "<div><div class=\"pf-account-row__name\">{name}</div>"
            "<div class=\"pf-account-row__location\">{location}</div></div>"
            "<div class=\"pf-account-row__amount\">{amount}</div>"
            "</div><div class=\"pf-account-row__track\">"
            "<div class=\"pf-account-row__bar{bar_class}\" style=\"width:{width:.2f}%\"></div>"
            "</div></div>".format(
                name=escape(str(account.account_name)),
                location=escape(str(account.account_location)),
                amount=escape(format_currency(balance)),
                bar_class=bar_class,
                width=bar_width,
            ),
            unsafe_allow_html=True,
        )
