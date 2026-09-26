"""Profile workspace for personal details and Account management."""

from __future__ import annotations

from datetime import date

import streamlit as st

from dashboard.components.account_form import render_account_form
from dashboard.components.account_movement_form import (
    MovementFormResult,
    render_adjustment_form,
    render_transfer_form,
)
from dashboard.components.goal_v2_form import render_goal_v2_form
from dashboard.utils.formatter import format_currency
from models.account import Account
from models.account_movement import AccountMovement
from models.goal import Goal
from models.user_settings import UserSettings
from services.account_service import AccountService
from services.account_movement_service import AccountMovementService
from services.goal_service import GoalService
from services.settings_service import SettingsService


def render() -> None:
    """Render the Profile workspace without direct Google Sheets access."""

    st.title("Profile")
    st.caption("Manage your financial setup, accounts, and goals.")
    settings_service = SettingsService()
    try:
        with st.spinner("Loading profile..."):
            settings = settings_service.load()
    except Exception:
        st.error("Unable to load profile. Default values are being used.")
        settings = UserSettings()

    with st.expander("Personal details", expanded=False):
        _render_personal(settings_service, settings)
    st.space("small")
    _render_financial_preferences(settings_service)
    st.space("small")
    _render_accounts()
    st.space("small")
    _render_goals()


def _render_personal(
    service: SettingsService,
    settings: UserSettings,
) -> None:
    """Render the existing Personal settings form in its new Profile home."""

    st.caption("Personal details used by the dashboard.")
    with st.form("profile_personal_form"):
        name = st.text_input("Name", value=settings.name)
        submitted = st.form_submit_button("Save Personal")
    if not submitted:
        return
    try:
        with st.spinner("Saving profile..."):
            service.save(
                UserSettings(
                    **{
                        **settings.to_dict(),
                        "name": name.strip(),
                    }
                )
            )
    except ValueError as error:
        st.error(str(error))
    except OSError:
        st.error("Unable to save profile. Please try again.")
    else:
        st.success("Personal profile saved.")


def _render_financial_preferences(service: SettingsService) -> None:
    """Render Profile-owned local planning preferences without Sheets access."""

    try:
        monthly_limit = service.get_monthly_spending_limit()
    except OSError:
        monthly_limit = 0
        st.error("Unable to load Financial Preferences. Please try again.")
    with st.container(border=True, key="profile-preferences"):
        _render_section_title("1", "Financial Preferences", "tune")
        with st.form("profile_financial_preferences_form"):
            with st.container(key="profile-preferences-control"):
                field, action = st.columns([2.4, 1], vertical_alignment="bottom")
                with field:
                    limit = int(
                        st.number_input(
                            "Monthly Spending Limit",
                            min_value=0,
                            value=monthly_limit,
                            step=50_000,
                            help="Set to 0 to disable Spending Risk monitoring.",
                        )
                    )
                    st.caption("Used by Financial Outlook to evaluate spending risk.")
                with action:
                    submitted = st.form_submit_button(
                        "Save Preferences",
                        icon=":material/save:",
                        width="stretch",
                    )
        if not submitted:
            return
        try:
            service.save_monthly_spending_limit(limit)
        except (OSError, ValueError) as error:
            st.error(str(error))
        else:
            st.success("Monthly Spending Limit saved.")


def _render_accounts() -> None:
    """Render the sole Account Management surface in Profile."""

    service = AccountService()
    movement_service = AccountMovementService()
    feedback = st.session_state.pop("profile_account_feedback", None)
    with st.container(border=True, key="profile-accounts"):
        heading, transfer, adjustment, action = st.columns(
            [3.6, 1.15, 1.35, 1.35],
            vertical_alignment="center",
        )
        with heading:
            _render_section_title("2", "Accounts", "account_balance_wallet")
        with transfer:
            transfer_requested = st.button(
                "Transfer",
                key="profile_create_transfer",
                icon=":material/swap_horiz:",
                width="stretch",
            )
        with adjustment:
            adjustment_requested = st.button(
                "Adjust Balance",
                key="profile_create_adjustment",
                icon=":material/tune:",
                width="stretch",
            )
        with action:
            if st.button(
                "Add Account",
                key="profile_add_account",
                type="primary",
                icon=":material/add:",
                width="stretch",
            ):
                _open_account_form()
        try:
            with st.spinner("Loading accounts..."):
                account_summaries = service.get_account_summaries()
                movements = movement_service.list_movements()
                linked_goals = {
                    goal.account_id: goal
                    for goal in GoalService().list_goals()
                    if goal.status in {"active", "paused"}
                }
        except Exception:
            st.error("Unable to load accounts. Please try again.")
            return
        active_accounts = [
            summary["account"]
            for summary in account_summaries
            if isinstance(summary["account"], Account)
            and summary["account"].status == "active"
        ]
        if transfer_requested:
            if len(active_accounts) < 2:
                st.warning("Create at least two active Accounts before making a transfer.")
            else:
                _open_movement_form("transfer")
        if adjustment_requested:
            if not active_accounts:
                st.warning("Create an active Account before creating an adjustment.")
            else:
                _open_movement_form("adjustment")
        if feedback:
            st.success(feedback)
        if not account_summaries:
            st.info("No Accounts yet. Add an Account to start tracking allocations.")
        active_summaries, archived_summaries = _split_account_summaries(
            account_summaries
        )
        if active_summaries:
            _render_account_grid(active_summaries, linked_goals)
        if archived_summaries:
            with st.expander("Archived Accounts", expanded=False):
                st.caption("Archived Accounts remain readable for historical integrity.")
                _render_account_grid(archived_summaries, linked_goals)

    with st.container(border=True, key="profile-transfers"):
        _render_section_title("3", "Account Transfers", "swap_horiz")
        _render_movement_history(movements, account_summaries)

    if st.session_state.get("profile_account_form_mode"):
        _render_account_dialog(service)
    if st.session_state.get("profile_account_deleting"):
        _render_account_delete_dialog(service)
    if st.session_state.get("profile_account_archiving"):
        _render_account_archive_dialog(service)
    if st.session_state.get("profile_account_movement_form"):
        _render_movement_dialog(active_accounts, account_summaries)
    if st.session_state.get("profile_account_movement_pending"):
        _render_movement_confirmation(movement_service)
    if st.session_state.get("profile_account_movement_deleting"):
        _render_movement_delete_dialog(movement_service)


def _render_account_grid(
    account_summaries: list[dict[str, object]],
    linked_goals: dict[str, Goal],
) -> None:
    """Render Account summaries in responsive Profile card rows."""

    for start in range(0, len(account_summaries), 3):
        columns = st.columns(3, gap="small")
        for column, summary in zip(columns, account_summaries[start:start + 3]):
            with column:
                _render_account_summary(summary, linked_goals)


def _render_account_summary(
    summary: dict[str, object],
    linked_goals: dict[str, Goal],
) -> None:
    """Render one Account using only AccountService summary data."""

    account = summary["account"]
    if not isinstance(account, Account):
        return
    current_balance = int(summary["current_balance"])
    has_activity = bool(summary["has_activity"])
    is_archived = account.status == "archived"
    with st.container(border=True, key=f"profile-account-card-{account.account_id}"):
        top, badge = st.columns([3, 1], vertical_alignment="center")
        with top:
            st.markdown(f"**{account.account_name}**")
            st.caption(account.account_location)
        with badge:
            st.markdown(
                f'<span class="pf-status-badge pf-status-badge--{account.status}">'
                f"{account.status.title()}</span>",
                unsafe_allow_html=True,
            )
        st.caption("Current Balance")
        st.markdown(
            f'<div class="pf-profile-account-balance">{format_currency(current_balance)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("Linked Goal")
        linked_goal = linked_goals.get(account.account_id)
        if linked_goal:
            st.caption(linked_goal.goal_id if False else "Goal linked")
        else:
            st.caption("—")
        edit, archive, delete = st.columns(3)
        with edit:
            if st.button(
                "Edit",
                key=f"profile_edit_account_{account.account_id}",
                icon=":material/edit:",
                width="stretch",
            ):
                _open_account_form(account)
        with archive:
            if st.button(
                "Archive",
                key=f"profile_archive_account_{account.account_id}",
                icon=":material/archive:",
                width="stretch",
                disabled=is_archived or current_balance != 0,
            ):
                _open_account_archive_confirmation(account)
        with delete:
            if st.button(
                "Delete",
                key=f"profile_delete_account_{account.account_id}",
                icon=":material/delete:",
                width="stretch",
                disabled=has_activity,
            ):
                _open_account_delete_confirmation(account)
        if not is_archived and current_balance != 0:
            st.caption(
                "Archive is available once the current balance is zero. "
                "Move or reconcile the remaining allocation first."
            )
        if has_activity:
            st.caption(
                "Initial Balance is locked and Delete is unavailable because this "
                "Account has activity. Use Adjust Balance to reconcile it."
            )


def _split_account_summaries(
    account_summaries: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Separate active and archived Account summaries for readable history."""

    active: list[dict[str, object]] = []
    archived: list[dict[str, object]] = []
    for summary in account_summaries:
        account = summary.get("account")
        if isinstance(account, Account) and account.status == "archived":
            archived.append(summary)
        else:
            active.append(summary)
    return active, archived


def _render_movement_history(
    movements: list[AccountMovement],
    account_summaries: list[dict[str, object]],
) -> None:
    """Render a compact, separate history for Transfers and Adjustments."""

    account_labels = {
        account.account_id: f"{account.account_name} — {account.account_location}"
        for summary in account_summaries
        if isinstance((account := summary["account"]), Account)
    }
    st.caption("Transfers and adjustments are separate from Income and Expense transactions.")
    if not movements:
        st.info("No Account Movements yet.")
        return
    for movement in movements[:5]:
        _render_movement_entry(movement, account_labels)
    if len(movements) > 5:
        with st.expander("View full movement history", expanded=False):
            for movement in movements[5:]:
                _render_movement_entry(movement, account_labels)


def _render_movement_entry(
    movement: AccountMovement,
    account_labels: dict[str, str],
) -> None:
    """Render one movement with its existing delete action intact."""

    movement_key = (
        f"profile-movement-{movement.movement_type}-{movement.movement_id}"
    )
    with st.container(border=True, key=movement_key):
        details, delete = st.columns([6, 1], vertical_alignment="center")
        with details:
            _render_movement_details(movement, account_labels)
        with delete:
            if st.button(
                "Delete",
                key=f"profile_delete_movement_{movement.movement_id}",
                icon=":material/delete:",
                width="stretch",
            ):
                st.session_state["profile_account_movement_deleting"] = movement


def _render_movement_details(
    movement: AccountMovement,
    account_labels: dict[str, str],
) -> None:
    """Render the compact, type-specific information for one movement."""

    movement_label = "Transfer" if movement.movement_type == "transfer" else "Adjustment"
    st.markdown(
        f'<span class="pf-movement-badge pf-movement-badge--{movement.movement_type}">'
        f"{movement_label}</span>",
        unsafe_allow_html=True,
    )
    if movement.movement_type == "transfer":
        source = _movement_account_label(movement.from_account_id, account_labels)
        destination = _movement_account_label(movement.to_account_id, account_labels)
        source_column, arrow_column, destination_column, amount_column = st.columns(
            [3, 0.45, 3, 1.35],
            vertical_alignment="center",
        )
        with source_column:
            st.write(source)
        with arrow_column:
            st.markdown(
                '<span class="material-symbols-rounded pf-movement-arrow">arrow_forward</span>',
                unsafe_allow_html=True,
            )
        with destination_column:
            st.write(destination)
        with amount_column:
            st.markdown(
                f'<div class="pf-movement-amount">{format_currency(movement.amount)}</div>',
                unsafe_allow_html=True,
            )
    else:
        account = _movement_account_label(movement.account_id, account_labels)
        amount_class = "positive" if movement.amount >= 0 else "negative"
        signed_amount = f"+{format_currency(movement.amount)}" if movement.amount >= 0 else format_currency(movement.amount)
        account_column, amount_column = st.columns([5, 1.35], vertical_alignment="center")
        with account_column:
            st.write(account)
        with amount_column:
            st.markdown(
                f'<div class="pf-movement-amount pf-movement-amount--{amount_class}">'
                f"Delta: {signed_amount}</div>",
                unsafe_allow_html=True,
            )
    st.caption(str(movement.date))
    if movement.note:
        st.caption(movement.note)


def _movement_account_label(
    account_id: str | None,
    account_labels: dict[str, str],
) -> str:
    """Render an archived or missing historical Account reference safely."""

    if not account_id:
        return "-"
    return account_labels.get(account_id, f"Historical Account ({account_id})")


def _open_movement_form(movement_type: str) -> None:
    """Open the Profile-owned form for a new Transfer or Adjustment."""

    st.session_state["profile_account_movement_form"] = movement_type


@st.dialog("Account Movement", dismissible=False, icon=":material/swap_horiz:")
def _render_movement_dialog(
    active_accounts: list[Account],
    account_summaries: list[dict[str, object]],
) -> None:
    """Collect movement inputs, then require the service-backed confirmation."""

    movement_type = st.session_state.get("profile_account_movement_form")
    balances = {
        account.account_id: int(summary["current_balance"])
        for summary in account_summaries
        if isinstance((account := summary["account"]), Account)
    }
    st.subheader("Transfer" if movement_type == "transfer" else "Adjustment")
    result = (
        render_transfer_form(active_accounts)
        if movement_type == "transfer"
        else render_adjustment_form(active_accounts, balances)
    )
    if result is None:
        return
    if result.action == "cancel":
        _close_movement_form()
        st.rerun()
    st.session_state["profile_account_movement_pending"] = {
        "movement_type": result.movement_type,
        "from_account_id": result.from_account_id,
        "to_account_id": result.to_account_id,
        "account_id": result.account_id,
        "amount": result.amount,
        "movement_date": result.movement_date,
        "note": result.note,
    }
    _close_movement_form()
    st.rerun()


@st.dialog("Confirm Account Movement", dismissible=False, icon=":material/check_circle:")
def _render_movement_confirmation(service: AccountMovementService) -> None:
    """Confirm movement inputs after showing their financial effect clearly."""

    pending = st.session_state.get("profile_account_movement_pending")
    if not isinstance(pending, dict):
        _close_movement_confirmation()
        st.rerun()
    movement_type = pending["movement_type"]
    try:
        if movement_type == "transfer":
            projected_balance = service.get_transfer_preview(
                str(pending["from_account_id"]),
                pending["amount"],
            )
            st.write("Confirm transfer")
            st.write(f"Amount: **{format_currency(int(pending['amount']))}**")
            if projected_balance < 0:
                st.warning(
                    "This transfer will make the source Account balance negative: "
                    f"{format_currency(projected_balance)}."
                )
        else:
            account_id = str(pending["account_id"])
            current, delta = service.get_adjustment_preview(
                account_id,
                pending["amount"],
            )
            st.write("Confirm adjustment")
            st.write(f"Current Balance: **{format_currency(current)}**")
            st.write(f"Actual Balance: **{format_currency(int(pending['amount']))}**")
            st.write(f"Adjustment Delta: **{format_currency(delta)}**")
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to prepare movement confirmation. Please try again.")
        return

    with st.container(horizontal=True):
        cancel_requested = st.button("Cancel", icon=":material/close:")
        confirm_requested = st.button(
            "Confirm",
            type="primary",
            icon=":material/check:",
        )
    if cancel_requested:
        _close_movement_confirmation()
        st.rerun()
    if not confirm_requested:
        return
    try:
        with st.spinner("Saving Account Movement..."):
            if movement_type == "transfer":
                service.create_transfer(
                    from_account_id=str(pending["from_account_id"]),
                    to_account_id=str(pending["to_account_id"]),
                    amount=pending["amount"],
                    movement_date=pending["movement_date"],
                    note=str(pending["note"]),
                )
                feedback = "Transfer created."
            else:
                service.create_adjustment(
                    account_id=str(pending["account_id"]),
                    actual_balance=pending["amount"],
                    movement_date=pending["movement_date"],
                    reason=str(pending["note"]),
                )
                feedback = "Adjustment created."
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to save Account Movement. Please try again.")
        return
    _close_movement_confirmation()
    st.session_state["profile_account_feedback"] = feedback
    st.rerun()


def _close_movement_form() -> None:
    """Clear temporary Profile state for the movement input dialog."""

    st.session_state.pop("profile_account_movement_form", None)


def _close_movement_confirmation() -> None:
    """Clear temporary Profile state for the movement confirmation dialog."""

    st.session_state.pop("profile_account_movement_pending", None)


@st.dialog("Delete Account Movement", dismissible=False, icon=":material/delete:")
def _render_movement_delete_dialog(service: AccountMovementService) -> None:
    """Confirm deletion by immutable Movement ID without compensating records."""

    movement = st.session_state.get("profile_account_movement_deleting")
    if not isinstance(movement, AccountMovement):
        _close_movement_delete_dialog()
        st.rerun()
    st.warning("Deleting this Movement recalculates affected Account balances.")
    st.write(f"**{movement.movement_type.title()}** · {movement.date}")
    st.write(format_currency(movement.amount))
    with st.container(horizontal=True):
        cancel_requested = st.button("Cancel", icon=":material/close:")
        delete_requested = st.button(
            "Confirm delete",
            type="primary",
            icon=":material/delete:",
        )
    if cancel_requested:
        _close_movement_delete_dialog()
        st.rerun()
    if not delete_requested:
        return
    try:
        with st.spinner("Deleting Account Movement..."):
            service.delete_movement(movement.movement_id)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to delete Account Movement. Please try again.")
        return
    _close_movement_delete_dialog()
    st.session_state["profile_account_feedback"] = "Account Movement deleted."
    st.rerun()


def _close_movement_delete_dialog() -> None:
    """Clear Profile state for the movement deletion dialog."""

    st.session_state.pop("profile_account_movement_deleting", None)


def _render_goals() -> None:
    """Render Goal V2 as Account-linked configuration and derived progress."""

    service = GoalService()
    feedback = st.session_state.pop("profile_goal_feedback", None)
    with st.container(border=True, key="profile-goals"):
        heading, action = st.columns([5, 1], vertical_alignment="center")
        with heading:
            _render_section_title("4", "Goals", "target")
        with action:
            if st.button(
                "Add Goal",
                key="profile_add_goal_v2",
                type="primary",
                icon=":material/add:",
                width="stretch",
            ):
                _open_goal_form()
        try:
            with st.spinner("Loading Goals..."):
                summaries = service.get_goal_summaries()
        except Exception:
            st.error("Unable to load Goals. Please try again.")
            return
        if feedback:
            st.success(feedback)
        if not summaries:
            st.info("No Goals yet. Add one to track an Account allocation.")
        for start in range(0, len(summaries), 2):
            columns = st.columns(2, gap="small")
            for column, summary in zip(columns, summaries[start:start + 2]):
                with column:
                    _render_goal_summary(summary)

    if st.session_state.get("profile_goal_form_mode"):
        _render_goal_dialog(service)
    if st.session_state.get("profile_goal_deleting"):
        _render_goal_delete_dialog(service)


def _render_goal_summary(summary: dict[str, object]) -> None:
    """Render one Goal V2 card from service-provided values only."""

    goal = summary["goal"]
    account = summary["account"]
    if not isinstance(goal, Goal):
        return
    with st.container(border=True, key=f"profile-goal-card-{goal.goal_id}"):
        details = st.container()
        with details:
            if isinstance(account, Account):
                st.write(f"**{account.account_name}**")
                st.caption(f"Location: {account.account_location}")
            else:
                st.write("**Historical Goal**")
                st.caption("Linked Account is unavailable.")
            current = summary["current_progress"]
            remaining = summary["remaining_amount"]
            progress = summary["progress_percent"]
            if isinstance(current, int) and isinstance(remaining, int) and isinstance(progress, float):
                st.write(
                    f"Progress: **{format_currency(current)}** / "
                    f"{format_currency(goal.target_amount)}"
                )
                st.caption(
                    f"Remaining: {format_currency(remaining)} · {progress:.1f}%"
                )
                st.progress(min(max(int(progress), 0), 100))
            st.caption(
                f"Deadline: {_goal_deadline_label(goal.deadline)} · "
                f"Priority: {goal.priority.title()} · Status: {goal.status.title()}"
            )
            health = str(summary["health"])
            st.markdown(
                f'<span class="pf-goal-badge pf-goal-badge--{_goal_health_class(health)}">'
                f"{health}</span>",
                unsafe_allow_html=True,
            )
            required = summary["required_monthly_contribution"]
            if isinstance(required, (int, float)):
                st.caption(
                    f"Required monthly contribution: {format_currency(int(required))}"
                )
            elif goal.deadline is None:
                st.caption("Required monthly contribution: N/A (no deadline)")
        edit, status, close, delete = st.columns(4)
        with edit:
            if st.button(
                "Edit",
                key=f"profile_edit_goal_{goal.goal_id}",
                icon=":material/edit:",
                width="stretch",
            ):
                _open_goal_form(goal, account if isinstance(account, Account) else None)
        with status:
            target_status = "active" if goal.status == "paused" else "paused"
            status_label = "Resume" if goal.status == "paused" else "Pause"
            if st.button(
                status_label,
                key=f"profile_toggle_goal_{goal.goal_id}",
                width="stretch",
                disabled=goal.status == "closed",
            ):
                _change_goal_status(goal.goal_id, target_status)
        with close:
            if st.button(
                "Close",
                key=f"profile_close_goal_{goal.goal_id}",
                icon=":material/check_circle:",
                width="stretch",
                disabled=goal.status == "closed",
            ):
                _change_goal_status(goal.goal_id, "closed")
        with delete:
            if st.button(
                "Delete",
                key=f"profile_delete_goal_{goal.goal_id}",
                icon=":material/delete:",
                width="stretch",
            ):
                st.session_state["profile_goal_deleting"] = goal


def _render_section_title(number: str, title: str, icon: str) -> None:
    """Render a consistent numbered Profile section title."""

    st.markdown(
        "<div class=\"pf-profile-section-title\">"
        f"<span class=\"material-symbols-rounded\">{icon}</span>"
        f"<span>{number}. {title}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def _goal_health_class(health: str) -> str:
    """Return a UI-only semantic class for a service-derived Goal health state."""

    normalized = health.strip().lower()
    if normalized in {"on track", "achieved"}:
        return "positive"
    if normalized in {"at risk", "limited"}:
        return "warning"
    if normalized in {"off track", "overdue"}:
        return "negative"
    return "neutral"


def _goal_deadline_label(deadline: str | None) -> str:
    """Return a safe, readable optional deadline label."""

    if not deadline:
        return "No deadline"
    try:
        return date.fromisoformat(deadline).strftime("%d %b %Y")
    except ValueError:
        return deadline


def _open_goal_form(goal: Goal | None = None, account: Account | None = None) -> None:
    """Open one Profile-owned Goal V2 form in Create or Edit mode."""

    st.session_state["profile_goal_form_mode"] = "edit" if goal else "create"
    if goal is not None:
        st.session_state["profile_goal_editing"] = goal
        st.session_state["profile_goal_editing_account"] = account
    else:
        st.session_state.pop("profile_goal_editing", None)
        st.session_state.pop("profile_goal_editing_account", None)


@st.dialog("Goal", dismissible=False, icon=":material/savings:")
def _render_goal_dialog(service: GoalService) -> None:
    """Create or edit Goal metadata through GoalService only."""

    mode = st.session_state.get("profile_goal_form_mode", "create")
    goal = st.session_state.get("profile_goal_editing")
    account = st.session_state.get("profile_goal_editing_account")
    try:
        eligible_accounts = service.get_eligible_accounts() if mode == "create" else []
    except Exception:
        st.error("Unable to load eligible Accounts. Please try again.")
        return
    if mode == "create" and not eligible_accounts:
        st.warning("No eligible active Account is available for a new Goal.")
        if st.button("Close"):
            _close_goal_form()
            st.rerun()
        return
    account_label = (
        f"{account.account_name} — {account.account_location}"
        if isinstance(account, Account)
        else "Historical Account"
    )
    result = render_goal_v2_form(
        mode="edit" if mode == "edit" else "create",
        accounts=eligible_accounts,
        goal=goal if isinstance(goal, Goal) else None,
        account_label=account_label,
    )
    if result is None:
        return
    if result.action == "cancel":
        _close_goal_form()
        st.rerun()
    try:
        with st.spinner("Saving Goal..."):
            if mode == "edit" and isinstance(goal, Goal):
                service.update_goal(
                    goal.goal_id,
                    target_amount=result.target_amount,
                    priority=result.priority,
                    deadline=result.deadline,
                )
                feedback = "Goal updated."
            else:
                service.create_goal(
                    account_id=str(result.account_id),
                    target_amount=result.target_amount,
                    priority=result.priority,
                    deadline=result.deadline,
                )
                feedback = "Goal created."
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to save Goal. Please try again.")
        return
    _close_goal_form()
    st.session_state["profile_goal_feedback"] = feedback
    st.rerun()


def _change_goal_status(goal_id: str, status: str) -> None:
    """Delegate one lifecycle transition to GoalService and rerun Profile."""

    try:
        with st.spinner("Updating Goal status..."):
            GoalService().set_goal_status(goal_id, status)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to update Goal status. Please try again.")
        return
    st.session_state["profile_goal_feedback"] = "Goal status updated."
    st.rerun()


def _close_goal_form() -> None:
    """Clear temporary Profile state for the Goal V2 form."""

    st.session_state.pop("profile_goal_form_mode", None)
    st.session_state.pop("profile_goal_editing", None)
    st.session_state.pop("profile_goal_editing_account", None)


@st.dialog("Delete Goal", dismissible=False, icon=":material/delete:")
def _render_goal_delete_dialog(service: GoalService) -> None:
    """Confirm deletion of a Goal configuration without touching finance data."""

    goal = st.session_state.get("profile_goal_deleting")
    if not isinstance(goal, Goal):
        _close_goal_delete_dialog()
        st.rerun()
    st.warning("Deleting a Goal does not change the Account, balance, or movements.")
    with st.container(horizontal=True):
        cancel_requested = st.button("Cancel", icon=":material/close:")
        delete_requested = st.button(
            "Confirm delete",
            type="primary",
            icon=":material/delete:",
        )
    if cancel_requested:
        _close_goal_delete_dialog()
        st.rerun()
    if not delete_requested:
        return
    try:
        with st.spinner("Deleting Goal..."):
            service.delete_goal(goal.goal_id)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to delete Goal. Please try again.")
        return
    _close_goal_delete_dialog()
    st.session_state["profile_goal_feedback"] = "Goal deleted."
    st.rerun()


def _close_goal_delete_dialog() -> None:
    """Clear temporary Profile state for Goal deletion confirmation."""

    st.session_state.pop("profile_goal_deleting", None)


def _open_account_form(account: Account | None = None) -> None:
    """Open the single reusable Account form in Create or Edit mode."""

    st.session_state["profile_account_form_mode"] = (
        "edit" if isinstance(account, Account) else "create"
    )
    if isinstance(account, Account):
        st.session_state["profile_account_editing"] = account
    else:
        st.session_state.pop("profile_account_editing", None)


@st.dialog("Account", dismissible=False, icon=":material/account_balance_wallet:")
def _render_account_dialog(service: AccountService) -> None:
    """Create or update one Account through AccountService only."""

    mode = st.session_state.get("profile_account_form_mode", "create")
    raw_account = st.session_state.get("profile_account_editing")
    account = raw_account if isinstance(raw_account, Account) else None
    try:
        initial_balance_editable = (
            True
            if mode == "create" or account is None
            else service.is_initial_balance_editable(account.account_id)
        )
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to load Account details. Please try again.")
        return

    result = render_account_form(
        mode="edit" if mode == "edit" else "create",
        account=account,
        initial_balance_editable=initial_balance_editable,
    )
    if result is None:
        return
    if result.action == "cancel":
        _close_account_form()
        st.rerun()

    try:
        with st.spinner("Saving Account..."):
            if mode == "edit" and account is not None:
                if (
                    initial_balance_editable
                    and result.initial_balance != account.initial_balance
                ):
                    service.update_initial_balance(account.account_id, result.initial_balance)
                service.update_account_metadata(
                    account.account_id,
                    account_name=result.account_name,
                    account_location=result.account_location,
                )
                message = "Account updated."
            else:
                service.create_account(
                    account_name=result.account_name,
                    account_location=result.account_location,
                    initial_balance=result.initial_balance,
                )
                message = "Account created."
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to save Account. Please try again.")
        return

    _close_account_form()
    st.session_state["profile_account_feedback"] = message
    st.rerun()


def _close_account_form() -> None:
    """Clear Profile-owned Account form state."""

    st.session_state.pop("profile_account_form_mode", None)
    st.session_state.pop("profile_account_editing", None)


def _open_account_delete_confirmation(account: Account) -> None:
    """Open confirmation for a service-eligible Account deletion."""

    st.session_state["profile_account_deleting"] = account


@st.dialog("Delete Account", dismissible=False, icon=":material/delete:")
def _render_account_delete_dialog(service: AccountService) -> None:
    """Confirm Account deletion and delegate eligibility to AccountService."""

    account = st.session_state.get("profile_account_deleting")
    if not isinstance(account, Account):
        _close_account_delete_dialog()
        st.rerun()
    st.warning("This deletes the Account metadata. Transactions are never deleted.")
    st.write(f"**{account.account_name}** · {account.account_location}")
    with st.container(horizontal=True):
        cancel_requested = st.button("Cancel", icon=":material/close:")
        delete_requested = st.button(
            "Confirm delete",
            type="primary",
            icon=":material/delete:",
        )
    if cancel_requested:
        _close_account_delete_dialog()
        st.rerun()
    if not delete_requested:
        return
    try:
        with st.spinner("Deleting Account..."):
            service.delete_account(account.account_id)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to delete Account. Please try again.")
        return
    _close_account_delete_dialog()
    st.session_state["profile_account_feedback"] = "Account deleted."
    st.rerun()


def _close_account_delete_dialog() -> None:
    """Clear Profile-owned Account delete confirmation state."""

    st.session_state.pop("profile_account_deleting", None)


def _open_account_archive_confirmation(account: Account) -> None:
    """Open confirmation for an Account archive action."""

    st.session_state["profile_account_archiving"] = account


@st.dialog("Archive Account", dismissible=False, icon=":material/archive:")
def _render_account_archive_dialog(service: AccountService) -> None:
    """Confirm Account archival through the lifecycle service rule."""

    account = st.session_state.get("profile_account_archiving")
    if not isinstance(account, Account):
        _close_account_archive_dialog()
        st.rerun()
    st.warning("Archived Accounts remain available for historical records.")
    st.write(f"**{account.account_name}** · {account.account_location}")
    with st.container(horizontal=True):
        cancel_requested = st.button("Cancel", icon=":material/close:")
        archive_requested = st.button(
            "Confirm archive",
            type="primary",
            icon=":material/archive:",
        )
    if cancel_requested:
        _close_account_archive_dialog()
        st.rerun()
    if not archive_requested:
        return
    try:
        with st.spinner("Archiving Account..."):
            service.archive_account(account.account_id)
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Unable to archive Account. Please try again.")
        return
    _close_account_archive_dialog()
    st.session_state["profile_account_feedback"] = "Account archived."
    st.rerun()


def _close_account_archive_dialog() -> None:
    """Clear Profile-owned Account archive confirmation state."""

    st.session_state.pop("profile_account_archiving", None)
