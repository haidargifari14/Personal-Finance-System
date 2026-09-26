"""Settings workspace for integrations and transaction data management."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import streamlit as st

from dashboard.components.integration_card import render_integration_card
from services.data_management_service import DataManagementService
from services.integration_service import IntegrationService, IntegrationStatus


def render() -> None:
    """Render the Settings workspace with isolated section failures."""

    st.title("Settings")
    st.caption("Manage app integrations and your financial data.")
    st.space("small")
    _render_section_safely("Integrations", _render_integrations)
    st.space("small")
    _render_section_safely("Data Management", _render_data_management)


def _render_integrations() -> None:
    """Render service-owned external integration status and health checks."""

    service = IntegrationService()
    telegram_key = "settings_telegram_integration_status"
    sheets_key = "settings_google_sheets_integration_status"
    st.session_state.setdefault(telegram_key, service.get_telegram_status())
    st.session_state.setdefault(sheets_key, service.get_google_sheets_status())
    feedback = st.session_state.pop("settings_integration_feedback", None)
    if feedback:
        message, is_success = feedback
        if is_success:
            st.success(message)
        else:
            st.error(message or "Connection check failed.")

    with st.container(border=True, key="settings-integrations"):
        _render_section_title("1", "Integrations", "power")
        telegram_column, sheets_column = st.columns(2, gap="small")
        with telegram_column:
            telegram_requested = render_integration_card(
                st.session_state[telegram_key],
                key="settings_telegram",
            )
        with sheets_column:
            sheets_requested = render_integration_card(
                st.session_state[sheets_key],
                key="settings_google_sheets",
            )

        if telegram_requested:
            _recheck_integration(
                service.test_telegram_connection,
                telegram_key,
                "Telegram connection checked.",
            )
        if sheets_requested:
            _recheck_integration(
                service.test_google_sheets_connection,
                sheets_key,
                "Google Sheets connection checked.",
            )


def _recheck_integration(
    check_connection: Callable[[], IntegrationStatus],
    state_key: str,
    success_message: str,
) -> None:
    """Run a service health check and refresh only its Settings-owned state."""

    with st.spinner("Checking connection..."):
        status: IntegrationStatus = check_connection()
    st.session_state[state_key] = status
    if status.state == "Connected":
        st.session_state["settings_integration_feedback"] = (success_message, True)
    else:
        st.session_state["settings_integration_feedback"] = (status.message, False)
    st.rerun()


def _render_section_safely(name: str, render_section: Callable[[], None]) -> None:
    """Keep unrelated Settings sections available after one rendering failure."""

    try:
        render_section()
    except Exception:
        with st.container(border=True):
            st.subheader(name)
            st.error(f"Unable to load {name.lower()}. Please try again.")


def _render_data_management() -> None:
    """Render Settings-owned controls for safe transaction data management."""

    backup_store = st.session_state.setdefault("settings_transaction_backups", {})
    service = DataManagementService(backup_store=backup_store)
    _render_data_management_feedback()
    with st.container(border=True, key="settings-data-management"):
        _render_section_title("2", "Data Management", "database")
        export_import, backup_restore = st.columns(2, gap="small")
        with export_import:
            with st.container(border=True, key="settings-export-import-card"):
                _render_export_section(service)
                _render_import_section(service)
        with backup_restore:
            with st.container(border=True, key="settings-backup-restore-card"):
                _render_backup_section(service)
                _render_restore_section(service)
        with st.container(border=True, key="settings-danger-zone"):
            _render_danger_zone(service)

    if st.session_state.get("settings_restore_backup_id"):
        _render_restore_confirmation(service)
    if st.session_state.get("settings_reset_confirmation_open"):
        _render_reset_confirmation(service)


def _render_export_section(service: DataManagementService) -> None:
    """Render full-dataset export controls using ReportService serialization."""

    st.markdown("#### Export data")
    csv_data = st.session_state.get("settings_export_csv")
    excel_data = st.session_state.get("settings_export_excel")
    prepare, csv, excel = st.columns(3, gap="small")
    with prepare:
        prepare_requested = st.button(
            "Prepare Export",
            key="settings_prepare_export",
            icon=":material/download:",
            width="stretch",
        )
    with csv:
        st.download_button(
            "Export CSV",
            data=csv_data or b"",
            file_name="personal-finance-transactions.csv",
            mime="text/csv",
            icon=":material/table_view:",
            disabled=csv_data is None,
            on_click="ignore",
            width="stretch",
        )
    with excel:
        st.download_button(
            "Export Excel",
            data=excel_data or b"",
            file_name="personal-finance-transactions.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            icon=":material/grid_on:",
            disabled=excel_data is None,
            on_click="ignore",
            width="stretch",
        )
    if prepare_requested:
        try:
            with st.spinner("Preparing complete transaction export..."):
                csv_data, excel_data = service.get_export_data()
        except Exception:
            st.error("Unable to prepare transaction export. Please try again.")
        else:
            st.session_state["settings_export_csv"] = csv_data
            st.session_state["settings_export_excel"] = excel_data
            st.success("Export files are ready to download.")


def _render_backup_section(service: DataManagementService) -> None:
    """Render explicitly scoped transaction-only backup controls."""

    st.markdown("#### Transaction-only backup")
    st.caption(
        "Backs up Transactions only. Accounts, Account Movements, and Goals "
        "are not included or changed by backup and restore."
    )
    backups = service.get_backups()
    if backups:
        latest_backup = backups[0]
        st.caption(
            "Last backup: "
            f"{latest_backup['created_at'].strftime('%d %b %Y %H:%M')} "
            f"({latest_backup['transaction_count']} transactions)"
        )
        st.success("Status: Success")
    else:
        st.warning("No backup yet.", icon=":material/warning:")

    backup_download = st.session_state.get("settings_transaction_backup_download")
    if isinstance(backup_download, bytes):
        st.download_button(
            "Download transaction backup",
            data=backup_download,
            file_name=st.session_state.get(
                "settings_transaction_backup_filename",
                "transactions-backup.json",
            ),
            mime="application/json",
            icon=":material/download:",
        )

    if st.button(
        "Create transaction-only backup",
        key="settings_create_backup",
        icon=":material/backup:",
    ):
        try:
            with st.spinner("Creating transaction backup..."):
                backup = service.create_backup()
        except Exception:
            st.error("Backup failed. Please try again.")
        else:
            st.session_state["settings_transaction_backup_download"] = (
                service.get_backup_download(backup["backup_id"])
            )
            st.session_state["settings_transaction_backup_filename"] = (
                f"{backup['backup_id']}.json"
            )
            st.session_state["settings_data_management_feedback"] = (
                "Transaction-only backup created with "
                f"{backup['transaction_count']} transactions."
            )
            st.rerun()


def _render_import_section(service: DataManagementService) -> None:
    """Render preview-first CSV/XLSX append import and backup restore controls."""

    st.markdown("#### Import data")
    upload, preview_action = st.columns([2.4, 1], vertical_alignment="bottom")
    with upload:
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel file",
            type=["csv", "xlsx"],
            key="settings_import_file",
        )
        st.caption("CSV/XLSX • Max 200MB")
    with preview_action:
        preview_requested = st.button(
            "Preview data",
            key="settings_preview_import",
            icon=":material/preview:",
            disabled=uploaded_file is None,
            width="stretch",
        )
    if preview_requested and uploaded_file is not None:
        try:
            with st.spinner("Validating import data..."):
                preview = service.preview_import(
                    uploaded_file.getvalue(),
                    uploaded_file.name,
                )
        except ValueError as error:
            st.error(str(error))
            st.session_state.pop("settings_import_preview", None)
        except Exception:
            st.error("Import failed. Please try again with a valid file.")
            st.session_state.pop("settings_import_preview", None)
        else:
            st.session_state["settings_import_preview"] = preview

    preview = st.session_state.get("settings_import_preview")
    if isinstance(preview, dict):
        errors = preview.get("errors", [])
        if errors:
            st.error("Import validation failed. No data will be imported.")
            st.write("\n".join(errors[:10]))
        else:
            transactions = preview["transactions"]
            duplicate_count = preview.get("duplicates", 0)
            st.caption(f"Validated transactions to append: {len(transactions)}")
            if duplicate_count:
                st.warning(f"{duplicate_count} exact duplicate rows will be skipped.")
            st.dataframe(transactions.head(10), width="stretch", hide_index=True)
            if st.button(
                "Import validated data",
                key="settings_confirm_import",
                type="primary",
                icon=":material/upload:",
                disabled=transactions.empty,
            ):
                try:
                    with st.spinner("Appending transactions..."):
                        count = service.import_transactions(
                            transactions.to_dict("records")
                        )
                except (ValueError, OSError):
                    st.error("Import failed. Existing transaction data was not changed.")
                except Exception:
                    st.error("Import failed. Please try again.")
                else:
                    _clear_dashboard_data_state()
                    st.session_state["settings_data_management_feedback"] = (
                        f"{count} transactions were imported successfully."
                    )
                    st.session_state.pop("settings_import_preview", None)
                    st.rerun()

def _render_restore_section(service: DataManagementService) -> None:
    """Render the transaction-only backup restore control."""

    st.markdown("#### Restore backup")
    backups = service.get_backups()
    if backups:
        backup_ids = [backup["backup_id"] for backup in backups]
        selected_backup = st.selectbox(
            "Transaction-only backup to restore",
            options=backup_ids,
            format_func=lambda backup_id: _format_backup_label(
                next(backup for backup in backups if backup["backup_id"] == backup_id)
            ),
        )
        if st.button(
            "Preview and restore backup",
            key="settings_restore_backup",
            icon=":material/restore:",
        ):
            try:
                preview = service.get_backup_preview(selected_backup)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state["settings_restore_backup_id"] = selected_backup
                st.session_state["settings_restore_backup_preview"] = preview
                st.rerun()


def _render_danger_zone(service: DataManagementService) -> None:
    """Render the two-step, transaction-only reset action."""

    st.markdown("#### Danger Zone")
    st.warning(
        "Reset Transaction Data deletes Transactions only. Accounts, Account "
        "Movements, Goals, Profile data, and application settings are preserved. "
        "Create a transaction-only backup before resetting."
    )
    if st.button(
        "Reset transaction data",
        key="settings_request_reset",
        type="secondary",
        icon=":material/delete_forever:",
    ):
        st.session_state["settings_reset_confirmation_open"] = True
        st.rerun()


@st.dialog("Restore transaction backup", dismissible=False, icon=":material/restore:")
def _render_restore_confirmation(service: DataManagementService) -> None:
    """Require confirmation before replacing transactions from a backup."""

    preview = st.session_state.get("settings_restore_backup_preview", {})
    st.warning(
        "This replaces all current Transaction data with this transaction-only "
        "backup. Accounts, Account Movements, and Goals are not changed."
    )
    st.write(
        f"**Backup:** {preview.get('created_at', '-') }  \\n"
        f"**Transactions:** {preview.get('transaction_count', 0)}"
    )
    with st.container(horizontal=True):
        restore_requested = st.button("Confirm restore", type="primary")
        cancel_requested = st.button("Cancel")
    if cancel_requested:
        _close_restore_dialog()
        st.rerun()
    if restore_requested:
        try:
            with st.spinner("Restoring transactions..."):
                count = service.restore_backup(
                    st.session_state["settings_restore_backup_id"]
                )
        except (ValueError, OSError):
            st.error("Unable to restore backup. Existing data was not changed.")
        except Exception:
            st.error("Unable to restore backup. Please try again.")
        else:
            _clear_dashboard_data_state()
            _close_restore_dialog()
            st.session_state["settings_data_management_feedback"] = (
                f"Transaction-only backup restored with {count} transactions."
            )
            st.rerun()


@st.dialog("Reset transaction data", dismissible=False, icon=":material/warning:")
def _render_reset_confirmation(service: DataManagementService) -> None:
    """Require typed confirmation before a transaction-only destructive reset."""

    st.error(
        "This permanently removes all Transaction data only. Accounts, Account "
        "Movements, Goals, Profile data, and application settings are preserved."
    )
    confirmation = st.text_input("Type RESET to confirm", key="settings_reset_text")
    with st.container(horizontal=True):
        reset_requested = st.button(
            "Confirm reset",
            type="primary",
            disabled=confirmation != "RESET",
        )
        cancel_requested = st.button("Cancel")
    if cancel_requested:
        st.session_state.pop("settings_reset_confirmation_open", None)
        st.session_state.pop("settings_reset_text", None)
        st.rerun()
    if reset_requested:
        try:
            with st.spinner("Resetting transaction data..."):
                service.reset_transactions()
        except Exception:
            st.error("Unable to reset transaction data. Please try again.")
        else:
            _clear_dashboard_data_state()
            st.session_state.pop("settings_reset_confirmation_open", None)
            st.session_state.pop("settings_reset_text", None)
            st.session_state["settings_data_management_feedback"] = (
                "Transaction data was reset. Accounts, Account Movements, Goals, "
                "Profile data, and Settings were preserved."
            )
            st.rerun()


def _render_data_management_feedback() -> None:
    """Display and consume the latest successful data-management result."""

    feedback = st.session_state.pop("settings_data_management_feedback", None)
    if feedback:
        st.success(feedback)


def _clear_dashboard_data_state() -> None:
    """Remove page-local stale data after a transaction bulk mutation."""

    st.cache_data.clear()
    for key in (
        "settings_export_csv",
        "settings_export_excel",
        "settings_import_preview",
        "settings_restore_backup_id",
        "settings_restore_backup_preview",
    ):
        st.session_state.pop(key, None)


def _close_restore_dialog() -> None:
    """Clear temporary restore confirmation state."""

    st.session_state.pop("settings_restore_backup_id", None)
    st.session_state.pop("settings_restore_backup_preview", None)


def _format_backup_label(backup: dict[str, object]) -> str:
    """Format one safe backup label for the Settings restore selector."""

    created_at = backup["created_at"]
    if not isinstance(created_at, datetime):
        return "Unknown backup"
    return (
        f"{created_at.strftime('%d %b %Y %H:%M')} "
        f"({backup['transaction_count']} transactions)"
    )


def _render_section_title(number: str, title: str, icon: str) -> None:
    """Render a consistent numbered Settings section title."""

    st.markdown(
        "<div class=\"pf-settings-section-title\">"
        f"<span class=\"material-symbols-rounded\">{icon}</span>"
        f"<span>{number}. {title}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
