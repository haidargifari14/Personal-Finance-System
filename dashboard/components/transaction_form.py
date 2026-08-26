"""Reusable dialog form for creating and editing dashboard transactions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Mapping

import streamlit as st

from services.category_definitions import categories_for_type
from models.account import Account

TRANSACTION_FORM_OPEN_KEY = "transaction_form_open"
TRANSACTION_FORM_MODE_KEY = "transaction_form_mode"
TRANSACTION_FORM_EDIT_DATA_KEY = "transaction_form_edit_data"
TRANSACTION_FORM_SUCCESS_KEY = "transaction_form_success"
TRANSACTION_FORM_SUBMITTING_KEY = "transaction_form_submitting"
TRANSACTION_FORM_TYPE_KEY = "transaction_form_type"
TRANSACTION_FORM_CATEGORY_KEY = "transaction_form_category"
TRANSACTION_FORM_ACCOUNT_KEY = "transaction_form_account"
TRANSACTION_FORM_EXPENSE_TYPE_KEY = "transaction_form_expense_type"
TRANSACTION_FORM_COVERAGE_MONTHS_KEY = "transaction_form_coverage_months"

CREATE_MODE = "create"
EDIT_MODE = "edit"
EXPENSE_TYPE_OPTIONS = ("Normal", "Periodic", "One-off")


def open_transaction_form(transaction: Mapping[str, Any] | None = None) -> None:
    """Open the transaction form in create or edit mode."""

    if transaction is None:
        st.session_state[TRANSACTION_FORM_MODE_KEY] = CREATE_MODE
        st.session_state.pop(TRANSACTION_FORM_EDIT_DATA_KEY, None)
        st.session_state[TRANSACTION_FORM_TYPE_KEY] = "Income"
        st.session_state[TRANSACTION_FORM_CATEGORY_KEY] = categories_for_type(
            "income"
        )[0]
        st.session_state[TRANSACTION_FORM_ACCOUNT_KEY] = ""
        st.session_state.pop(TRANSACTION_FORM_EXPENSE_TYPE_KEY, None)
        st.session_state.pop(TRANSACTION_FORM_COVERAGE_MONTHS_KEY, None)
    else:
        st.session_state[TRANSACTION_FORM_MODE_KEY] = EDIT_MODE
        st.session_state[TRANSACTION_FORM_EDIT_DATA_KEY] = dict(transaction)
        existing_type = str(transaction.get("type", "income")).strip().lower()
        normalized_type = "Expense" if existing_type == "expense" else "Income"
        st.session_state[TRANSACTION_FORM_TYPE_KEY] = normalized_type
        st.session_state[TRANSACTION_FORM_CATEGORY_KEY] = str(
            transaction.get("category", "")
        ).strip()
        st.session_state[TRANSACTION_FORM_ACCOUNT_KEY] = str(
            transaction.get("account_id") or ""
        ).strip()
        existing_expense_type = str(
            transaction.get("expense_type") or "normal"
        ).strip().lower()
        st.session_state[TRANSACTION_FORM_EXPENSE_TYPE_KEY] = {
            "normal": "Normal",
            "periodic": "Periodic",
            "one-off": "One-off",
        }.get(existing_expense_type, "Normal")
        st.session_state[TRANSACTION_FORM_COVERAGE_MONTHS_KEY] = _to_coverage_months(
            transaction.get("coverage_months")
        )
    st.session_state[TRANSACTION_FORM_OPEN_KEY] = True


def consume_transaction_success_message() -> str | None:
    """Return and clear the most recent form success message."""

    return st.session_state.pop(TRANSACTION_FORM_SUCCESS_KEY, None)


def render_transaction_form(
    on_create: Callable[[dict[str, Any]], None],
    on_update: Callable[[str, dict[str, Any]], None],
    active_accounts: list[Account],
) -> None:
    """Render the reusable transaction dialog when it is open."""

    if st.session_state.get(TRANSACTION_FORM_OPEN_KEY):
        _render_transaction_dialog(on_create, on_update, active_accounts)


@st.dialog("Transaction", dismissible=False, icon=":material/receipt_long:")
def _render_transaction_dialog(
    on_create: Callable[[dict[str, Any]], None],
    on_update: Callable[[str, dict[str, Any]], None],
    active_accounts: list[Account],
) -> None:
    """Collect transaction data and delegate persistence to page callbacks."""

    mode = st.session_state.get(TRANSACTION_FORM_MODE_KEY, CREATE_MODE)
    edit_data = st.session_state.get(TRANSACTION_FORM_EDIT_DATA_KEY, {})
    is_edit_mode = mode == EDIT_MODE and isinstance(edit_data, dict)
    type_options = ("Income", "Expense")
    action_label = "Save changes" if is_edit_mode else "Save"
    is_submitting = st.session_state.get(TRANSACTION_FORM_SUBMITTING_KEY, False)

    st.subheader("Edit transaction" if is_edit_mode else "Add transaction")
    transaction_type = st.selectbox(
        "Transaction type",
        options=type_options,
        key=TRANSACTION_FORM_TYPE_KEY,
        on_change=_reset_category_for_selected_type,
        disabled=is_submitting,
    )
    category_options = _category_options(
        transaction_type,
        edit_data if is_edit_mode else None,
    )
    if st.session_state.get(TRANSACTION_FORM_CATEGORY_KEY) not in category_options:
        st.session_state[TRANSACTION_FORM_CATEGORY_KEY] = category_options[0]
    category = st.selectbox(
        "Category",
        options=category_options,
        key=TRANSACTION_FORM_CATEGORY_KEY,
        disabled=is_submitting,
    )
    account_options, account_labels = _account_options(
        active_accounts,
        edit_data if is_edit_mode else None,
    )
    if st.session_state.get(TRANSACTION_FORM_ACCOUNT_KEY) not in account_options:
        st.session_state[TRANSACTION_FORM_ACCOUNT_KEY] = account_options[0]
    account_id = st.selectbox(
        "Account",
        options=account_options,
        key=TRANSACTION_FORM_ACCOUNT_KEY,
        format_func=lambda value: account_labels[value],
        disabled=is_submitting,
    )
    expense_type, coverage_months = _render_expense_classification(
        is_edit_mode=is_edit_mode,
        transaction_type=transaction_type,
        disabled=is_submitting,
    )

    with st.form("transaction_form", border=False):
        transaction_date = st.date_input(
            "Date",
            value=_to_date(edit_data.get("date")) if is_edit_mode else None,
            format="DD/MM/YYYY",
        )
        amount = st.number_input(
            "Amount",
            min_value=0,
            value=_to_amount(edit_data.get("amount")) if is_edit_mode else None,
            placeholder="Enter amount",
            step=1000,
        )
        note = st.text_area(
            "Note (optional)",
            value=str(edit_data.get("note", "")) if is_edit_mode else "",
            placeholder="Add a note",
        )

        with st.container(horizontal=True):
            save_requested = st.form_submit_button(
                action_label,
                type="primary",
                icon=":material/save:",
                disabled=is_submitting,
            )
            cancel_requested = st.form_submit_button(
                "Cancel",
                icon=":material/close:",
            )

    if cancel_requested:
        _close_transaction_form()
        st.rerun()

    if not save_requested:
        return
    if st.session_state.get(TRANSACTION_FORM_SUBMITTING_KEY, False):
        return

    st.session_state[TRANSACTION_FORM_SUBMITTING_KEY] = True
    try:
        form_data = {
            "date": transaction_date,
            "transaction_type": transaction_type,
            "category": category,
            "amount": amount,
            "note": note,
            "account_id": account_id or None,
            "expense_type": expense_type,
            "coverage_months": coverage_months,
        }
        with st.spinner(
            "Memperbarui transaksi..." if is_edit_mode else "Menyimpan transaksi..."
        ):
            if is_edit_mode:
                on_update(str(edit_data["transaction_id"]), form_data)
            else:
                on_create(form_data)
    except ValueError as error:
        st.session_state.pop(TRANSACTION_FORM_SUBMITTING_KEY, None)
        st.error(str(error))
        return
    except Exception:
        st.session_state.pop(TRANSACTION_FORM_SUBMITTING_KEY, None)
        st.error("Gagal menyimpan transaksi. Silakan coba lagi.")
        return

    _close_transaction_form()
    st.session_state[TRANSACTION_FORM_SUCCESS_KEY] = (
        "Transaksi berhasil diperbarui."
        if is_edit_mode
        else "Transaksi berhasil disimpan."
    )
    st.rerun()


def _close_transaction_form() -> None:
    """Clear temporary form state after saving or cancelling."""

    st.session_state[TRANSACTION_FORM_OPEN_KEY] = False
    st.session_state.pop(TRANSACTION_FORM_MODE_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_EDIT_DATA_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_SUBMITTING_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_TYPE_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_CATEGORY_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_ACCOUNT_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_EXPENSE_TYPE_KEY, None)
    st.session_state.pop(TRANSACTION_FORM_COVERAGE_MONTHS_KEY, None)


def _reset_category_for_selected_type() -> None:
    """Choose a safe default when the transaction type changes."""

    transaction_type = st.session_state.get(TRANSACTION_FORM_TYPE_KEY, "Income")
    categories = categories_for_type(transaction_type)
    if categories:
        st.session_state[TRANSACTION_FORM_CATEGORY_KEY] = categories[0]
    st.session_state[TRANSACTION_FORM_EXPENSE_TYPE_KEY] = "Normal"
    st.session_state.pop(TRANSACTION_FORM_COVERAGE_MONTHS_KEY, None)


def _render_expense_classification(
    *,
    is_edit_mode: bool,
    transaction_type: str,
    disabled: bool,
) -> tuple[str | None, int | None]:
    """Render classification controls only while editing an Expense record."""

    if not is_edit_mode or transaction_type.strip().lower() != "expense":
        return None, None

    expense_type = st.selectbox(
        "Expense type",
        options=EXPENSE_TYPE_OPTIONS,
        key=TRANSACTION_FORM_EXPENSE_TYPE_KEY,
        disabled=disabled,
    )
    if expense_type != "Periodic":
        st.session_state.pop(TRANSACTION_FORM_COVERAGE_MONTHS_KEY, None)
        return expense_type, None

    coverage_months = st.number_input(
        "Coverage months",
        min_value=1,
        step=1,
        key=TRANSACTION_FORM_COVERAGE_MONTHS_KEY,
        disabled=disabled,
        help="Jumlah bulan yang dicakup oleh pembayaran Periodic.",
    )
    return expense_type, int(coverage_months)


def _category_options(
    transaction_type: str,
    edit_data: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Return type-specific options while preserving one legacy edit value."""

    normalized_type = transaction_type.strip().lower()
    options = categories_for_type(normalized_type)
    legacy_category = ""
    if edit_data and str(edit_data.get("type", "")).strip().lower() == normalized_type:
        legacy_category = str(edit_data.get("category", "")).strip()
    if legacy_category and legacy_category not in options:
        return (legacy_category, *options)
    return options


def _account_options(
    active_accounts: list[Account],
    edit_data: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Build Account choices while keeping legacy or archived links readable."""

    labels = {
        account.account_id: f"{account.account_name} — {account.account_location}"
        for account in active_accounts
    }
    existing_account_id = ""
    if edit_data:
        existing_account_id = str(edit_data.get("account_id") or "").strip()
    if existing_account_id and existing_account_id not in labels:
        labels[existing_account_id] = "Archived account (historical link)"
    if edit_data and not existing_account_id:
        labels[""] = "No linked account (legacy transaction)"
    return tuple(labels), labels


def _to_date(value: Any) -> date | None:
    """Convert persisted transaction dates to a date widget value."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _to_amount(value: Any) -> int | None:
    """Convert a stored amount to a safe number-input value."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)

    try:
        normalized = str(value).replace(".", "").replace(",", "")
        return int(normalized)
    except (TypeError, ValueError):
        return None


def _to_coverage_months(value: Any) -> int | None:
    """Convert a persisted optional coverage value for the edit widget."""

    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        coverage = int(value)
    except (TypeError, ValueError):
        return None
    return coverage if coverage >= 1 else None
