"""Reusable Goal V2 form that never accepts manual balance inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import streamlit as st

from models.account import Account
from models.goal import Goal


@dataclass(frozen=True)
class GoalV2FormResult:
    """Submitted Goal V2 data before Profile delegates it to GoalService."""

    action: Literal["save", "cancel"]
    account_id: str | None = None
    target_amount: int = 0
    priority: str = "medium"
    deadline: date | None = None


def render_goal_v2_form(
    *,
    mode: Literal["create", "edit"],
    accounts: list[Account],
    goal: Goal | None = None,
    account_label: str = "",
) -> GoalV2FormResult | None:
    """Render a Goal V2 create/edit form without service or balance logic."""

    is_edit = mode == "edit" and goal is not None
    account_ids = tuple(account.account_id for account in accounts)
    labels = {
        account.account_id: f"{account.account_name} — {account.account_location}"
        for account in accounts
    }
    with st.form("profile_goal_v2_form", border=False):
        if is_edit:
            st.text_input("Account", value=account_label, disabled=True)
            account_id = goal.account_id
        else:
            account_id = st.selectbox(
                "Account",
                options=account_ids,
                format_func=lambda value: labels[value],
            )
        target_amount = st.number_input(
            "Target Amount",
            min_value=1,
            value=goal.target_amount if is_edit else 1,
            step=50_000,
        )
        priority_options = ("high", "medium", "low")
        priority = st.selectbox(
            "Priority",
            priority_options,
            index=priority_options.index(goal.priority) if is_edit and goal.priority in priority_options else 1,
        )
        has_deadline = st.checkbox(
            "Set deadline",
            value=bool(goal and goal.deadline),
        )
        default_deadline = _parse_deadline(goal.deadline) if goal else date.today()
        deadline_value = st.date_input(
            "Deadline",
            value=default_deadline or date.today(),
            format="DD/MM/YYYY",
            disabled=not has_deadline,
        )
        with st.container(horizontal=True):
            cancel_requested = st.form_submit_button("Cancel", icon=":material/close:")
            save_requested = st.form_submit_button(
                "Save changes" if is_edit else "Create Goal",
                type="primary",
                icon=":material/save:",
            )
    if cancel_requested:
        return GoalV2FormResult(action="cancel")
    if not save_requested:
        return None
    return GoalV2FormResult(
        action="save",
        account_id=account_id,
        target_amount=int(target_amount),
        priority=priority,
        deadline=deadline_value if has_deadline else None,
    )


def _parse_deadline(value: str | None) -> date | None:
    """Return a date widget value for an optional persisted ISO deadline."""

    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
