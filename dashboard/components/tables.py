"""
dashboard/components/tables.py

Reusable table components for the
Personal Finance Dashboard.
"""

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_date
from dashboard.utils.theme import TABLE_HEIGHT

TRANSACTION_COLUMNS = ["date", "category", "type", "amount", "note"]
MANAGEMENT_TRANSACTION_COLUMNS = [*TRANSACTION_COLUMNS, "action"]
TRANSACTION_TYPE_LABELS = {
    "income": "Income",
    "expense": "Expense",
}
TRANSACTION_TYPE_BADGES = {
    "Income": "\U0001F7E2 Income",
    "Expense": "\U0001F534 Expense",
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

    display_data = _format_transaction_data(data)

    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        column_config={
            "date": st.column_config.TextColumn("Date", width="medium"),
            "category": st.column_config.TextColumn("Category", width="medium"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "amount": st.column_config.TextColumn("Amount", width="medium"),
            "note": st.column_config.TextColumn("Note", width="large"),
        },
    )


def transaction_management_table(
    data: pd.DataFrame,
    *,
    empty_message: str = "No transactions found for the selected filters.",
) -> dict[str, Any] | None:
    """Display transactions and return the selected row action, if any."""

    if data.empty:
        empty_table(empty_message)
        return None

    display_data = _format_transaction_data(data)
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
            "date": st.column_config.TextColumn("Date", width="medium"),
            "category": st.column_config.TextColumn("Category", width="medium"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "amount": st.column_config.TextColumn("Amount", width="medium"),
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


def _format_transaction_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return transaction data formatted for the dashboard table."""

    display_data = data.copy()

    if "date" in display_data:
        dates = pd.to_datetime(display_data["date"], errors="coerce")
        display_data["date"] = dates.apply(
            lambda value: format_date(value) if pd.notna(value) else "-"
        )

    if "type" in display_data:
        display_data["type"] = display_data["type"].replace(
            TRANSACTION_TYPE_LABELS
        )

    if "amount" in display_data:
        display_data["amount"] = display_data["amount"].apply(format_currency)

    if "note" in display_data:
        display_data["note"] = (
            display_data["note"].fillna("").astype(str).str.strip().replace("", "-")
        )

    available_columns = [
        column for column in TRANSACTION_COLUMNS if column in display_data
    ]
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
