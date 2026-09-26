"""Safe transaction-only export, import, backup, restore, and reset operations."""

from __future__ import annotations

import json
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile

import pandas as pd

from services.finance_service import FinanceService
from services.report_service import ReportService
from services.sheet_service import SheetService
from services.transaction_schema import (
    EXPORT_COLUMNS,
    is_valid_transaction_id,
    normalize_account_id,
    normalize_expense_metadata,
)


class DataManagementService:
    """Manage Transactions through existing service and repository layers.

    Backups intentionally cover only the Transactions worksheet in V2. Account,
    Account Movement, and Goal datasets are not represented in a snapshot and
    are never changed by a transaction backup restore or reset.
    """

    IMPORT_COLUMNS = ("Date", "Type", "Category", "Amount", "Note")
    V2_IMPORT_COLUMNS = EXPORT_COLUMNS[:7]
    V3_IMPORT_COLUMNS = EXPORT_COLUMNS

    def __init__(
        self,
        sheet_service: SheetService | None = None,
        backup_directory: Path | None = None,
        backup_store: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Initialize transaction dependencies and an ephemeral backup store.

        ``backup_directory`` is retained for call compatibility but is never
        read or written. Backups live only in the supplied process/session store
        and should be downloaded by the user for durable retention.
        """

        del backup_directory
        self._sheet_service = sheet_service
        self._backup_store = backup_store if backup_store is not None else {}

    def get_export_data(self) -> tuple[bytes, bytes]:
        """Return complete transaction data serialized as CSV and XLSX."""

        export_data = ReportService.prepare_transaction_export(
            self._transactions_dataframe()
        )
        return ReportService.export_csv(export_data), ReportService.export_excel(export_data)

    def create_backup(self) -> dict[str, Any]:
        """Create an ephemeral transaction-only snapshot for restore/download."""

        transactions = self._records_from_dataframe(self._transactions_dataframe())
        created_at = datetime.now()
        backup_id = created_at.strftime("transactions-%Y%m%d-%H%M%S-%f")
        payload = {
            "scope": "transactions_only",
            "excluded_datasets": ["accounts", "account_movements", "goals"],
            "created_at": created_at.isoformat(),
            "transaction_count": len(transactions),
            "transactions": transactions,
        }
        self._backup_store[backup_id] = payload
        return {"backup_id": backup_id, **payload}

    def get_backups(self) -> list[dict[str, Any]]:
        """Return transaction-only backups held in the current process/session."""

        backups = []
        for backup_id, payload in self._backup_store.items():
            try:
                self._validate_backup_payload(payload)
                timestamp = datetime.fromisoformat(str(payload["created_at"]))
                transaction_count = int(payload["transaction_count"])
            except (TypeError, ValueError, KeyError):
                continue
            backups.append(
                {
                    "backup_id": backup_id,
                    "created_at": timestamp,
                    "transaction_count": transaction_count,
                    "scope": "transactions_only",
                }
            )
        return sorted(backups, key=lambda backup: backup["created_at"], reverse=True)

    def get_backup_download(self, backup_id: str) -> bytes:
        """Serialize one ephemeral backup for an explicit user download."""

        return json.dumps(self._load_backup(backup_id), indent=2).encode("utf-8")

    def get_backup_preview(self, backup_id: str) -> dict[str, Any]:
        """Validate a backup before any transaction-only destructive restore."""

        payload = self._load_backup(backup_id)
        transactions, errors = self._validate_records(payload["transactions"])
        if errors:
            raise ValueError("Selected backup contains invalid transaction data.")
        return {
            "backup_id": backup_id,
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "transaction_count": len(transactions),
            "transactions": pd.DataFrame(transactions),
            "scope": str(payload.get("scope", "transactions_only")),
            "excluded_datasets": payload.get(
                "excluded_datasets",
                ["accounts", "account_movements", "goals"],
            ),
        }

    def restore_backup(self, backup_id: str) -> int:
        """Restore one ephemeral backup after schema and identity validation."""

        return self._restore_backup_payload(self._load_backup(backup_id))

    def preview_backup_content(self, content: bytes) -> dict[str, Any]:
        """Validate a downloaded backup payload without using server storage."""

        payload = self._decode_backup_content(content)
        transactions, errors = self._validate_records(payload["transactions"])
        if errors:
            raise ValueError("Selected backup contains invalid transaction data.")
        return {
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "transaction_count": len(transactions),
            "transactions": pd.DataFrame(transactions),
            "scope": "transactions_only",
            "excluded_datasets": payload["excluded_datasets"],
        }

    def restore_backup_content(self, content: bytes) -> int:
        """Restore uploaded backup bytes without requiring local backup files."""

        return self._restore_backup_payload(self._decode_backup_content(content))

    def preview_import(self, content: bytes, file_name: str) -> dict[str, Any]:
        """Read and validate an uploaded CSV or XLSX without writing data."""

        imported_data = self._read_uploaded_data(content, file_name)
        normalized_data = self._normalize_import_columns(imported_data)
        transactions, errors = self._validate_records(normalized_data.to_dict("records"))
        if errors:
            return {"transactions": pd.DataFrame(), "errors": errors, "duplicates": 0}

        unique_transactions, duplicate_count = self._remove_existing_duplicates(
            transactions
        )
        return {
            "transactions": pd.DataFrame(unique_transactions),
            "errors": [],
            "duplicates": duplicate_count,
        }

    def import_transactions(self, transactions: list[dict[str, Any]]) -> int:
        """Append a fully validated transaction collection to Google Sheets."""

        validated_transactions, errors = self._validate_records(transactions)
        if errors:
            raise ValueError("Import contains invalid transaction data.")
        self._get_sheet_service().append_many(validated_transactions)
        return len(validated_transactions)

    def reset_transactions(self) -> None:
        """Remove Transactions only while preserving every other V2 dataset."""

        self._get_sheet_service().replace_transactions([])

    def _transactions_dataframe(self) -> pd.DataFrame:
        """Return a normalized transaction dataframe from the shared repository."""

        dataframe = self._get_sheet_service().get_transactions_dataframe()
        if dataframe.empty:
            return pd.DataFrame(
                columns=[
                    "transaction_id",
                    "date",
                    "type",
                    "category",
                    "amount",
                    "note",
                    "account_id",
                    "expense_type",
                    "coverage_months",
                    "row_number",
                ]
            )
        return dataframe

    @staticmethod
    def _records_from_dataframe(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
        """Return stable repository records from a normalized dataframe."""

        if dataframe.empty:
            return []
        records = []
        for record in dataframe.to_dict("records"):
            transaction_type = str(record.get("type", "")).strip().lower()
            expense_type, coverage_months = normalize_expense_metadata(
                transaction_type,
                record.get("expense_type"),
                record.get("coverage_months"),
            )
            records.append(
                {
                    "date": str(record.get("date", ""))[:10],
                    "type": transaction_type,
                    "category": str(record.get("category", "")).strip(),
                    "amount": int(record.get("amount", 0)),
                    "note": str(record.get("note", "") or "").strip(),
                    "transaction_id": str(record.get("transaction_id", "")).strip(),
                    "account_id": normalize_account_id(record.get("account_id")),
                    "expense_type": expense_type,
                    "coverage_months": coverage_months,
                }
            )
        return records

    def _validate_records(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Validate every record before an all-or-nothing bulk operation."""

        finance_service = FinanceService()
        transactions: list[dict[str, Any]] = []
        errors: list[str] = []
        transaction_ids: set[str] = set()
        for row_number, record in enumerate(records, start=2):
            try:
                raw_date = pd.to_datetime(record.get("date"), errors="raise").date()
                transaction = finance_service.prepare_transaction(
                    transaction_date=raw_date,
                    transaction_type=str(record.get("type", "")),
                    category=str(record.get("category", "")),
                    amount=record.get("amount"),
                    note=str(record.get("note", "") or ""),
                    account_id=normalize_account_id(record.get("account_id")),
                    expense_type=record.get("expense_type"),
                    coverage_months=record.get("coverage_months"),
                )
                supplied_id = str(record.get("transaction_id", "") or "").strip()
                if supplied_id:
                    if not is_valid_transaction_id(supplied_id):
                        raise ValueError("Invalid transaction ID.")
                    if supplied_id in transaction_ids:
                        raise ValueError("Duplicate transaction ID.")
                    transaction["transaction_id"] = supplied_id
                transaction_ids.add(transaction["transaction_id"])
            except (TypeError, ValueError):
                errors.append(f"Row {row_number} has invalid transaction data.")
            else:
                transactions.append(transaction)
        return transactions, errors

    def _remove_existing_duplicates(
        self,
        transactions: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        """Remove exact duplicates already stored or repeated in an import file."""

        existing_transactions = self._records_from_dataframe(
            self._transactions_dataframe()
        )
        existing_ids = {
            transaction["transaction_id"]
            for transaction in existing_transactions
            if transaction.get("transaction_id")
        }
        duplicate_ids = {
            transaction["transaction_id"]
            for transaction in transactions
            if transaction["transaction_id"] in existing_ids
        }
        if duplicate_ids:
            raise ValueError("Import contains Transaction IDs that already exist.")

        existing_keys = {
            self._transaction_key(transaction)
            for transaction in existing_transactions
        }
        unique_transactions = []
        duplicate_count = 0
        for transaction in transactions:
            transaction_key = self._transaction_key(transaction)
            if transaction_key in existing_keys:
                duplicate_count += 1
                continue
            existing_keys.add(transaction_key)
            unique_transactions.append(transaction)
        return unique_transactions, duplicate_count

    @staticmethod
    def _transaction_key(
        transaction: dict[str, Any],
    ) -> tuple[str, str, str, int, str, str | None, str | None, int | None]:
        """Build a stable signature for safe exact duplicate detection."""

        return (
            str(transaction["date"]),
            str(transaction["type"]).lower(),
            str(transaction["category"]),
            int(transaction["amount"]),
            str(transaction.get("note", "")),
            normalize_account_id(transaction.get("account_id")),
            transaction.get("expense_type"),
            transaction.get("coverage_months"),
        )

    def _load_backup(self, backup_id: str) -> dict[str, Any]:
        """Load one ephemeral backup identifier without filesystem access."""

        if not backup_id.startswith("transactions-") or "/" in backup_id or "\\" in backup_id:
            raise ValueError("Selected backup was not found.")
        try:
            payload = self._backup_store[backup_id]
            self._validate_backup_payload(payload)
            return payload
        except (KeyError, TypeError, ValueError):
            raise ValueError("Selected backup was not found.") from None

    @staticmethod
    def _validate_backup_payload(payload: dict[str, Any]) -> None:
        """Validate the non-financial envelope required by backup operations."""

        if payload.get("scope") != "transactions_only":
            raise ValueError("Unsupported backup scope.")
        if not isinstance(payload.get("transactions"), list):
            raise ValueError("Backup transactions are invalid.")
        datetime.fromisoformat(str(payload["created_at"]))
        int(payload["transaction_count"])
        if payload.get("excluded_datasets") != [
            "accounts",
            "account_movements",
            "goals",
        ]:
            raise ValueError("Backup scope metadata is invalid.")

    def _decode_backup_content(self, content: bytes) -> dict[str, Any]:
        """Decode a user-provided JSON backup entirely in memory."""

        try:
            payload = json.loads(content.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
            self._validate_backup_payload(payload)
            return payload
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            raise ValueError("Selected backup was not found.") from None

    def _restore_backup_payload(self, payload: dict[str, Any]) -> int:
        """Restore a validated backup payload through the transaction repository."""

        transactions, errors = self._validate_records(payload["transactions"])
        if errors:
            raise ValueError("Selected backup contains invalid transaction data.")
        self._get_sheet_service().replace_transactions(transactions)
        return len(transactions)

    def _get_sheet_service(self) -> SheetService:
        """Return the shared Google Sheets repository only when data is needed."""

        if self._sheet_service is None:
            self._sheet_service = SheetService()
        return self._sheet_service

    def _read_uploaded_data(self, content: bytes, file_name: str) -> pd.DataFrame:
        """Read supported CSV or XLSX content using no additional client layer."""

        suffix = Path(file_name).suffix.lower()
        if suffix == ".csv":
            try:
                return pd.read_csv(BytesIO(content))
            except (UnicodeDecodeError, pd.errors.ParserError):
                raise ValueError("Import failed: unable to read CSV data.") from None
        if suffix == ".xlsx":
            return self._read_xlsx(content)
        raise ValueError("Import failed: upload a CSV or Excel (.xlsx) file.")

    def _normalize_import_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize the user-facing import column structure."""

        columns = {str(column).strip().lower(): column for column in dataframe.columns}
        v3_columns = {column.lower() for column in self.V3_IMPORT_COLUMNS}
        v2_columns = {column.lower() for column in self.V2_IMPORT_COLUMNS}
        required = {column.lower() for column in self.IMPORT_COLUMNS}
        missing_columns = required.difference(columns)
        if missing_columns:
            raise ValueError("Import failed: invalid column structure.")
        selected_columns = (
            self.V3_IMPORT_COLUMNS
            if v3_columns.issubset(columns)
            else self.V2_IMPORT_COLUMNS
            if v2_columns.issubset(columns)
            else self.IMPORT_COLUMNS
        )
        normalized_names = {
            "Transaction ID": "transaction_id",
            "Date": "date",
            "Type": "type",
            "Category": "category",
            "Amount": "amount",
            "Note": "note",
            "Account ID": "account_id",
            "Expense Type": "expense_type",
            "Coverage Months": "coverage_months",
        }
        normalized = pd.DataFrame(
            {
                normalized_names[column]: dataframe[columns[column.lower()]]
                for column in selected_columns
            }
        )
        return normalized.fillna("")

    @staticmethod
    def _read_xlsx(content: bytes) -> pd.DataFrame:
        """Read basic XLSX workbooks, including files exported by this dashboard."""

        namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        try:
            with ZipFile(BytesIO(content)) as workbook:
                shared_strings = []
                if "xl/sharedStrings.xml" in workbook.namelist():
                    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
                    shared_strings = [
                        "".join(item.itertext())
                        for item in root.findall("main:si", namespace)
                    ]
                root = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        except Exception:
            raise ValueError("Import failed: unable to read Excel data.") from None

        rows = []
        for row in root.findall(".//main:row", namespace):
            values = []
            for cell in row.findall("main:c", namespace):
                cell_type = cell.get("t")
                value = cell.findtext("main:v", default="", namespaces=namespace)
                if cell_type == "inlineStr":
                    value = "".join(cell.itertext())
                elif cell_type == "s":
                    value = shared_strings[int(value)]
                values.append(value)
            rows.append(values)
        if not rows:
            return pd.DataFrame(columns=DataManagementService.IMPORT_COLUMNS)
        return pd.DataFrame(rows[1:], columns=rows[0])
