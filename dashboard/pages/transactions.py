"""Transactions workspace page for the Personal Finance Dashboard."""

import streamlit as st

from dashboard.components.confirmation_dialog import (
    consume_delete_success_message,
    open_delete_confirmation,
    render_delete_confirmation,
)
from dashboard.components.export_menu import render_transaction_export_menu
from dashboard.components.transaction_form import (
    consume_transaction_success_message,
    open_transaction_form,
    render_transaction_form,
)
from dashboard.components.filters.global_filter import get_global_filter_values
from dashboard.components.filters.transaction_filter import (
    TRANSACTION_SEARCH_KEY,
    render_transaction_filter,
)
from dashboard.components.tables import (
    clear_transaction_action_state,
    transaction_management_table,
)
from dashboard.components.toolbar import render_transaction_toolbar
from dashboard.utils.formatter import format_datetime
from services.analytics_service import AnalyticsService
from services.account_service import AccountService
from services.finance_service import FinanceService
from services.report_service import ReportService
from services.sheet_service import SheetService


def render() -> None:
    """Render the Transactions workspace."""

    st.title("Transactions")
    (
        search,
        add_requested,
        refresh_requested,
        export_container,
    ) = render_transaction_toolbar(TRANSACTION_SEARCH_KEY)
    success_messages = (
        consume_transaction_success_message(),
        consume_delete_success_message(),
    )
    for success_message in success_messages:
        if success_message:
            st.success(success_message)

    try:
        loading_message = (
            "Memperbarui transaksi dari Google Sheets..."
            if refresh_requested
            else "Memuat transaksi dari Google Sheets..."
        )
        with st.spinner(loading_message):
            analytics = AnalyticsService()
            if refresh_requested:
                analytics.clear_cache()
                SheetService.invalidate_read_cache("accounts")
                clear_transaction_action_state()

            start_date, end_date = get_global_filter_values()
            active_accounts = AccountService().list_active_accounts()
            categories = analytics.get_categories()
            transaction_filters = render_transaction_filter(categories, search)
            transactions = analytics.get_transactions(
                start_date=start_date,
                end_date=end_date,
                category=transaction_filters["category"],
                transaction_type=transaction_filters["transaction_type"],
                search=transaction_filters["search"],
                minimum_amount=transaction_filters["minimum_amount"],
                maximum_amount=transaction_filters["maximum_amount"],
                sort_by=transaction_filters["sort_by"],
                sort_order=transaction_filters["sort_order"],
            )
            transaction_summary = analytics.get_transaction_summary(
                start_date=start_date,
                end_date=end_date,
                category=transaction_filters["category"],
                transaction_type=transaction_filters["transaction_type"],
                search=transaction_filters["search"],
                minimum_amount=transaction_filters["minimum_amount"],
                maximum_amount=transaction_filters["maximum_amount"],
                sort_by=transaction_filters["sort_by"],
                sort_order=transaction_filters["sort_order"],
            )
    except ValueError as error:
        st.error(str(error))
        return
    except Exception:
        st.error("Gagal membaca transaksi. Silakan coba lagi.")
        st.caption(
            "Periksa koneksi internet, akses Google Sheets, dan kredensial aplikasi."
        )
        return

    if add_requested:
        clear_transaction_action_state()
        if not active_accounts:
            st.warning(
                "Buat akun aktif terlebih dahulu melalui Profile → Accounts sebelum menambah transaksi."
            )
        else:
            open_transaction_form()

    if export_container.open:
        _render_transaction_export(export_container, transactions)

    with st.container(border=True):
        st.subheader("Transaction Table")
        st.caption(f"Showing {len(transactions)} transactions")
        selected_action = transaction_management_table(
            transactions,
            empty_message=_get_empty_transaction_message(transaction_filters),
        )

    _render_transaction_summary(transaction_summary)

    if selected_action:
        clear_transaction_action_state()
        if selected_action["action"] == "Edit":
            open_transaction_form(selected_action["transaction"])
        elif selected_action["action"] == "Delete":
            open_delete_confirmation(selected_action["transaction"])

    render_transaction_form(_save_transaction, _update_transaction, active_accounts)
    render_delete_confirmation(_delete_transaction)


def _save_transaction(form_data: dict[str, object]) -> None:
    """Pass dashboard form data to FinanceService for validation and storage."""

    FinanceService().save_transaction(
        transaction_date=form_data["date"],
        transaction_type=str(form_data["transaction_type"]),
        category=str(form_data["category"]),
        amount=form_data["amount"],
        note=str(form_data["note"]),
        account_id=str(form_data["account_id"] or "") or None,
        expense_type=(
            str(form_data["expense_type"])
            if form_data.get("expense_type") is not None
            else None
        ),
        coverage_months=form_data.get("coverage_months"),
    )
    clear_transaction_action_state()


def _update_transaction(transaction_id: str, form_data: dict[str, object]) -> None:
    """Pass edited dashboard form data to FinanceService for persistence."""

    FinanceService().update_transaction(
        transaction_id,
        transaction_date=form_data["date"],
        transaction_type=str(form_data["transaction_type"]),
        category=str(form_data["category"]),
        amount=form_data["amount"],
        note=str(form_data["note"]),
        account_id=str(form_data["account_id"] or "") or None,
        expense_type=(
            str(form_data["expense_type"])
            if form_data.get("expense_type") is not None
            else None
        ),
        coverage_months=form_data.get("coverage_months"),
    )
    clear_transaction_action_state()


def _delete_transaction(transaction_id: str) -> None:
    """Pass a selected transaction row to FinanceService for deletion."""

    FinanceService().delete_transaction(transaction_id)
    clear_transaction_action_state()


def _render_transaction_export(export_container, transactions) -> None:
    """Prepare filtered exports only when the toolbar popover is open."""

    if transactions.empty:
        render_transaction_export_menu(
            export_container,
            csv_data=None,
            excel_data=None,
            file_stem="personal_finance_transactions",
        )
        return

    try:
        with st.spinner("Menyiapkan file export..."):
            export_data = ReportService.prepare_transaction_export(transactions)
            csv_data = ReportService.export_csv(export_data)
            excel_data = ReportService.export_excel(export_data)
    except Exception:
        st.error("Gagal menyiapkan file export. Silakan coba lagi.")
        return

    render_transaction_export_menu(
        export_container,
        csv_data=csv_data,
        excel_data=excel_data,
        file_stem="personal_finance_transactions",
    )


def _get_empty_transaction_message(transaction_filters: dict[str, object]) -> str:
    """Explain whether a Transactions empty state is caused by local filters."""

    has_local_filter = any(
        (
            transaction_filters["search"],
            transaction_filters["category"] != "All",
            transaction_filters["transaction_type"] != "All",
            transaction_filters["minimum_amount"] is not None,
            transaction_filters["maximum_amount"] is not None,
            transaction_filters["sort_by"] != "Date",
            transaction_filters["sort_order"] != "Descending",
        )
    )
    if has_local_filter:
        return "No transactions found for the selected filters."
    return "No transactions found for the selected global date range."


def _render_transaction_summary(summary: dict[str, object]) -> None:
    """Display concise, pagination-ready context for the active result set."""

    last_updated = summary.get("last_updated")
    last_updated_text = (
        format_datetime(last_updated) if last_updated is not None else "-"
    )
    with st.container(border=True):
        st.subheader("Transaction summary")
        with st.container(horizontal=True, vertical_alignment="center"):
            st.write(f"**Showing:** {summary['showing']} / {summary['total']}")
            st.write(f"**Filtered From:** {summary['filtered_from']}")
            st.write(f"**Last Updated:** {last_updated_text}")
