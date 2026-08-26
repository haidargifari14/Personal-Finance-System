"""Reusable confirmation dialog for destructive dashboard actions."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import pandas as pd
import streamlit as st

from dashboard.utils.formatter import format_currency, format_date

DELETE_DIALOG_OPEN_KEY = "transaction_delete_dialog_open"
DELETE_DIALOG_DATA_KEY = "transaction_delete_dialog_data"
DELETE_SUCCESS_KEY = "transaction_delete_success"


def open_delete_confirmation(transaction: Mapping[str, Any]) -> None:
    """Open the delete confirmation for one selected transaction."""

    st.session_state[DELETE_DIALOG_DATA_KEY] = dict(transaction)
    st.session_state[DELETE_DIALOG_OPEN_KEY] = True


def consume_delete_success_message() -> str | None:
    """Return and clear the latest successful-delete message."""

    return st.session_state.pop(DELETE_SUCCESS_KEY, None)


def render_delete_confirmation(on_confirm: Callable[[str], None]) -> None:
    """Render the delete confirmation when it has been requested."""

    if st.session_state.get(DELETE_DIALOG_OPEN_KEY):
        _render_delete_dialog(on_confirm)


@st.dialog("Delete transaction", dismissible=False, icon=":material/delete:")
def _render_delete_dialog(on_confirm: Callable[[str], None]) -> None:
    """Confirm a destructive transaction deletion before calling the page."""

    transaction = st.session_state.get(DELETE_DIALOG_DATA_KEY, {})
    if not isinstance(transaction, dict):
        _close_delete_confirmation()
        st.rerun()

    st.warning("This transaction will be permanently deleted.")
    _render_transaction_details(transaction)

    with st.container(horizontal=True):
        confirm_requested = st.button(
            "Confirm delete",
            type="primary",
            icon=":material/delete:",
        )
        cancel_requested = st.button("Cancel", icon=":material/close:")

    if cancel_requested:
        _close_delete_confirmation()
        st.rerun()

    if not confirm_requested:
        return

    try:
        with st.spinner("Menghapus transaksi..."):
            on_confirm(str(transaction["transaction_id"]))
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Gagal menghapus transaksi. Silakan coba lagi.")
        return

    _close_delete_confirmation()
    st.session_state[DELETE_SUCCESS_KEY] = "Transaksi berhasil dihapus."
    st.rerun()


def _render_transaction_details(transaction: Mapping[str, Any]) -> None:
    """Display the selected transaction in a concise confirmation summary."""

    transaction_date = pd.to_datetime(transaction.get("date"), errors="coerce")
    formatted_date = (
        format_date(transaction_date) if pd.notna(transaction_date) else "-"
    )
    transaction_type = str(transaction.get("type", "")).strip().title() or "-"

    with st.container(border=True):
        st.write(f"**Date:** {formatted_date}")
        st.write(f"**Category:** {transaction.get('category', '-')}")
        st.write(f"**Type:** {transaction_type}")
        st.write(f"**Amount:** {format_currency(transaction.get('amount', 0))}")


def _close_delete_confirmation() -> None:
    """Clear delete-dialog state after confirmation or cancellation."""

    st.session_state[DELETE_DIALOG_OPEN_KEY] = False
    st.session_state.pop(DELETE_DIALOG_DATA_KEY, None)
