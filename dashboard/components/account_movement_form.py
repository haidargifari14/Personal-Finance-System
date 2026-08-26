"""Minimal reusable forms for Account Transfers and Adjustments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import streamlit as st

from models.account import Account


@dataclass(frozen=True)
class MovementFormResult:
    """Represent submitted movement input before service confirmation."""

    action: Literal["save", "cancel"]
    movement_type: Literal["transfer", "adjustment"]
    from_account_id: str | None = None
    to_account_id: str | None = None
    account_id: str | None = None
    amount: int = 0
    movement_date: date | None = None
    note: str = ""


def render_transfer_form(accounts: list[Account]) -> MovementFormResult | None:
    """Render a Transfer form without loading data or applying business rules."""

    account_ids, labels = _account_options(accounts)
    source_id = st.selectbox(
        "From Account",
        account_ids,
        format_func=lambda account_id: labels[account_id],
        key="profile_transfer_source_account",
    )
    destination_id = st.selectbox(
        "To Account",
        account_ids,
        format_func=lambda account_id: labels[account_id],
        key="profile_transfer_destination_account",
    )
    with st.form("profile_transfer_form", border=False):
        amount = st.number_input("Amount", min_value=1, value=1, step=50_000)
        movement_date = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        note = st.text_area("Note (optional)")
        cancel_requested, save_requested = _form_actions("Create transfer")
    if cancel_requested:
        return MovementFormResult(action="cancel", movement_type="transfer")
    if not save_requested:
        return None
    return MovementFormResult(
        action="save",
        movement_type="transfer",
        from_account_id=source_id,
        to_account_id=destination_id,
        amount=int(amount),
        movement_date=movement_date,
        note=note,
    )


def render_adjustment_form(
    accounts: list[Account],
    balances: dict[str, int],
) -> MovementFormResult | None:
    """Render an Adjustment form and display its current derived balance."""

    account_ids, labels = _account_options(accounts)
    account_id = st.selectbox(
        "Account",
        account_ids,
        format_func=lambda value: labels[value],
        key="profile_adjustment_account",
    )
    st.text_input(
        "Current Balance",
        value=_format_balance(balances.get(account_id, 0)),
        disabled=True,
    )
    with st.form("profile_adjustment_form", border=False):
        actual_balance = st.number_input("Actual Balance", value=0, step=50_000)
        movement_date = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        reason = st.text_area("Reason")
        cancel_requested, save_requested = _form_actions("Create adjustment")
    if cancel_requested:
        return MovementFormResult(action="cancel", movement_type="adjustment")
    if not save_requested:
        return None
    return MovementFormResult(
        action="save",
        movement_type="adjustment",
        account_id=account_id,
        amount=int(actual_balance),
        movement_date=movement_date,
        note=reason,
    )


def _account_options(accounts: list[Account]) -> tuple[tuple[str, ...], dict[str, str]]:
    """Return stable Account ID options with user-readable labels."""

    labels = {
        account.account_id: f"{account.account_name} — {account.account_location}"
        for account in accounts
    }
    return tuple(labels), labels


def _form_actions(label: str) -> tuple[bool, bool]:
    """Render standard cancel and primary submit buttons for movement forms."""

    with st.container(horizontal=True):
        cancel_requested = st.form_submit_button("Cancel", icon=":material/close:")
        save_requested = st.form_submit_button(
            label,
            type="primary",
            icon=":material/save:",
        )
    return cancel_requested, save_requested


def _format_balance(amount: int) -> str:
    """Format a balance without importing dashboard-wide UI dependencies."""

    prefix = "-" if amount < 0 else ""
    return f"{prefix}Rp{abs(amount):,}".replace(",", ".")
