"""Reusable Create and Edit form for Account metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from models.account import Account


@dataclass(frozen=True)
class AccountFormResult:
    """Represent one Account form save or cancel action."""

    action: Literal["save", "cancel"]
    account_name: str = ""
    account_location: str = ""
    initial_balance: int = 0


def render_account_form(
    *,
    mode: Literal["create", "edit"],
    account: Account | None = None,
    initial_balance_editable: bool = True,
) -> AccountFormResult | None:
    """Render one reusable Account form without accessing services directly."""

    existing_account = account or Account(
        account_id="",
        account_name="",
        account_location="",
        initial_balance=0,
        tracking_start_date="",
        status="active",
        created_at="",
        updated_at="",
    )
    action_label = "Save changes" if mode == "edit" else "Create account"

    with st.form("settings_account_form", border=False):
        account_name = st.text_input(
            "Account Name",
            value=existing_account.account_name,
        )
        account_location = st.text_input(
            "Account Location",
            value=existing_account.account_location,
        )
        initial_balance = st.number_input(
            "Initial Balance",
            value=existing_account.initial_balance,
            step=50_000,
            disabled=mode == "edit" and not initial_balance_editable,
            help=(
                "Initial Balance is locked because this Account has activity."
                if mode == "edit" and not initial_balance_editable
                else "Money allocated before Account tracking began; not Income."
            ),
        )
        if mode == "edit" and not initial_balance_editable:
            st.info(
                "Initial Balance cannot be changed after the Account has activity."
            )
        with st.container(horizontal=True):
            cancel_requested = st.form_submit_button(
                "Cancel",
                icon=":material/close:",
            )
            save_requested = st.form_submit_button(
                action_label,
                type="primary",
                icon=":material/save:",
            )

    if cancel_requested:
        return AccountFormResult(action="cancel")
    if not save_requested:
        return None
    return AccountFormResult(
        action="save",
        account_name=account_name,
        account_location=account_location,
        initial_balance=int(initial_balance),
    )
