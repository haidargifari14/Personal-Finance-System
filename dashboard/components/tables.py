"""
dashboard/components/tables.py

Reusable table components for the
Personal Finance Dashboard.
"""

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_date
from dashboard.utils.theme import TABLE_HEIGHT

TRANSACTION_COLUMNS = ["date", "category", "type", "amount", "note"]
MANAGEMENT_TRANSACTION_COLUMNS = [
    "date",
    "category",
    "type",
    "account",
    "amount",
    "note",
    "action",
]
TRANSACTION_TYPE_LABELS = {
    "income": "Income",
    "expense": "Expense",
}
OVERVIEW_TRANSACTION_TYPE_LABELS = {
    "income": "● Income",
    "expense": "● Expense",
}
TRANSACTION_TYPE_BADGES = {
    "Income": "● Income",
    "Expense": "● Expense",
}
ACTION_OPTIONS = ["View", "Edit", "Delete"]
TRANSACTION_ACTION_KEY = "transaction_table_action"


def simple_table(
    data: pd.DataFrame,
    *,
    width: str | int = "stretch",
    hide_index: bool = True,
):
    """
    Display a generic dataframe.
    """

    st.dataframe(
        data,
        width=width,
        hide_index=hide_index,
        height=TABLE_HEIGHT,
    )


def transaction_table(
    data: pd.DataFrame,
) -> None:
    """Display a user-ready, formatted transaction history table."""

    if data.empty:
        empty_table("Belum ada transaksi untuk filter yang dipilih.")
        return

    display_data = _format_transaction_data(data, decorate_type=True)

    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        height="auto",
        row_height=34,
        column_config={
            "date": st.column_config.TextColumn("Date", width="small"),
            "category": st.column_config.TextColumn("Category", width="medium"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "amount": st.column_config.TextColumn(
                "Amount",
                width="medium",
                alignment="right",
            ),
            "note": st.column_config.TextColumn("Note", width="large"),
        },
    )


def transaction_management_table(
    data: pd.DataFrame,
    *,
    account_names: Mapping[str, str] | None = None,
    empty_message: str = "No transactions found for the selected filters.",
) -> dict[str, Any] | None:
    """Display transactions and return the selected row action, if any."""

    if data.empty:
        empty_table(empty_message)
        return None

    display_data = _format_transaction_data(
        data,
        account_names=account_names,
        include_account=True,
    )
    display_data["type"] = display_data["type"].replace(
        TRANSACTION_TYPE_BADGES
    )
    display_data["action"] = [ACTION_OPTIONS] * len(display_data)
    display_data = display_data.reindex(columns=MANAGEMENT_TRANSACTION_COLUMNS)

    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        column_config={
            "date": st.column_config.TextColumn("Date", width="small"),
            "category": st.column_config.TextColumn("Category", width="medium"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "account": st.column_config.TextColumn("Account", width="medium"),
            "amount": st.column_config.TextColumn(
                "Amount",
                width="medium",
                alignment="right",
            ),
            "note": st.column_config.TextColumn("Note", width="large"),
            "action": st.column_config.ButtonColumn(
                "Action",
                alignment="right",
                on_click=_record_transaction_action,
                key=TRANSACTION_ACTION_KEY,
            ),
        },
    )

    action_event = st.session_state.get(TRANSACTION_ACTION_KEY)
    if not isinstance(action_event, dict):
        return None

    row_index = action_event.get("row")
    action = action_event.get("label")
    if not isinstance(row_index, int) or action not in ACTION_OPTIONS:
        return None
    if row_index < 0 or row_index >= len(data):
        return None

    return {
        "action": action,
        "transaction": data.iloc[row_index].to_dict(),
    }


def category_transaction_table(data: pd.DataFrame) -> None:
    """Render selected-category transaction evidence with compact fields."""

    if data.empty:
        empty_table("Belum ada transaksi untuk kategori yang dipilih.")
        return

    display_data = _format_transaction_data(data)
    evidence_columns = [
        column for column in ("date", "amount", "note") if column in display_data
    ]
    st.dataframe(
        display_data[evidence_columns],
        width="stretch",
        hide_index=True,
        height="auto",
        row_height=32,
        column_config={
            "date": st.column_config.TextColumn("Date", width="medium"),
            "amount": st.column_config.TextColumn(
                "Amount",
                width="medium",
                alignment="right",
            ),
            "note": st.column_config.TextColumn("Note", width="large"),
        },
    )


def _format_transaction_data(
    data: pd.DataFrame,
    *,
    decorate_type: bool = False,
    account_names: Mapping[str, str] | None = None,
    include_account: bool = False,
) -> pd.DataFrame:
    """Return transaction data formatted for the dashboard table."""

    display_data = data.copy()

    if "date" in display_data:
        dates = pd.to_datetime(display_data["date"], errors="coerce")
        display_data["date"] = dates.apply(
            lambda value: format_date(value) if pd.notna(value) else "-"
        )

    if "type" in display_data:
        labels = (
            OVERVIEW_TRANSACTION_TYPE_LABELS
            if decorate_type
            else TRANSACTION_TYPE_LABELS
        )
        display_data["type"] = display_data["type"].replace(labels)

    if "amount" in display_data:
        display_data["amount"] = display_data["amount"].apply(format_currency)

    if "account_id" in display_data:
        account_lookup = account_names or {}
        display_data["account"] = display_data["account_id"].apply(
            lambda account_id: account_lookup.get(str(account_id or "").strip(), "—")
        )
    elif "account" not in display_data:
        display_data["account"] = "—"

    if "note" in display_data:
        display_data["note"] = (
            display_data["note"].fillna("").astype(str).str.strip().replace("", "-")
        )

    column_order = TRANSACTION_COLUMNS.copy()
    if include_account:
        column_order.insert(3, "account")
    available_columns = [column for column in column_order if column in display_data]
    return display_data[available_columns]


def empty_table(
    message: str = "Belum ada data untuk ditampilkan."
):
    """
    Display a consistent empty table state.
    """

    st.info(message)


def _record_transaction_action() -> None:
    """Receive the ButtonColumn event for the current Streamlit rerun."""


def clear_transaction_action_state() -> None:
    """Remove the temporary row-action event after its lifecycle ends."""

    st.session_state.pop(TRANSACTION_ACTION_KEY, None)
