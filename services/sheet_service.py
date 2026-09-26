"""
services/sheet_service.py

Data access layer for Google Sheets.

All interactions with Google Sheets should go through this service.
Business logic must NOT be implemented here.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable

import gspread
import pandas as pd

from services.google_credentials import get_google_credentials

from config import (
    ACCOUNTS_WORKSHEET_NAME,
    ACCOUNT_MOVEMENTS_WORKSHEET_NAME,
    GOALS_WORKSHEET_NAME,
    SPREADSHEET_NAME,
    WORKSHEET_NAME,
)
from services.account_movement_schema import (
    MOVEMENT_PHYSICAL_HEADERS,
    movement_record_to_sheet_row,
    movement_sheet_record_to_movement,
    normalize_movement,
)
from services.goal_schema import (
    GOAL_PHYSICAL_HEADERS,
    goal_record_to_sheet_row,
    goal_sheet_record_to_goal,
    normalize_goal,
)
from services.account_schema import (
    ACCOUNT_PHYSICAL_HEADERS,
    account_record_to_sheet_row,
    account_sheet_record_to_account,
    normalize_account_record,
)
from services.transaction_schema import (
    LEGACY_HEADERS,
    PHYSICAL_HEADERS,
    SHEET_HEADERS,
    TRANSACTION_FIELDS,
    new_transaction_id,
    normalize_transaction,
    records_to_sheet_rows,
    sheet_record_to_transaction,
)


LOGGER = logging.getLogger(__name__)


class SheetsReadError(RuntimeError):
    """Raised when a Google Sheets read cannot safely provide data."""


class _CachedDataset:
    """Keep one immutable-at-rest snapshot and its load metadata."""

    def __init__(self, records: list[dict[str, Any]], loaded_at: datetime) -> None:
        self.records = records
        self.loaded_at = loaded_at
        self.loaded_monotonic = time.monotonic()
        self.is_stale = False
        self.warning: str | None = None


class SheetService:
    """Repository layer for Google Sheets with shared, bounded read snapshots.

    The cache is intentionally owned here rather than by individual domain
    services. A Streamlit rerun can therefore construct multiple services while
    reusing one recent snapshot of each physical worksheet.
    """

    CACHE_TTL_SECONDS = 45
    MAX_READ_ATTEMPTS = 3
    RETRY_DELAYS_SECONDS = (0.25, 0.75)
    _DATASETS = ("transactions", "accounts", "account_movements", "goals")
    _cache_lock = threading.RLock()
    _read_cache: dict[str, _CachedDataset] = {}
    _read_metrics: dict[str, dict[str, int]] = {
        dataset: {"remote_reads": 0, "cache_hits": 0}
        for dataset in _DATASETS
    }
    _shared_resources: tuple[Any, Any, Any, Any, Any] | None = None

    def __init__(self) -> None:
        """Reuse one initialized workbook connection for the running process."""

        with self._cache_lock:
            resources = self._shared_resources
            if resources is None:
                creds = get_google_credentials()
                client = gspread.authorize(creds)
                spreadsheet = client.open(SPREADSHEET_NAME)
                self._spreadsheet = spreadsheet
                self._worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
                self._ensure_transaction_schema()
                self._accounts_worksheet = self._get_or_create_accounts_worksheet()
                self._account_movements_worksheet = (
                    self._get_or_create_account_movements_worksheet()
                )
                self._goals_worksheet = self._get_or_create_goals_worksheet()
                resources = (
                    self._spreadsheet,
                    self._worksheet,
                    self._accounts_worksheet,
                    self._account_movements_worksheet,
                    self._goals_worksheet,
                )
                type(self)._shared_resources = resources

            (
                self._spreadsheet,
                self._worksheet,
                self._accounts_worksheet,
                self._account_movements_worksheet,
                self._goals_worksheet,
            ) = resources

    # ==========================================================
    # CREATE
    # ==========================================================

    def append(self, transaction: dict) -> None:
        """Append a new transaction."""

        normalized = normalize_transaction(transaction, generate_missing_id=True)
        self._worksheet.append_row(records_to_sheet_rows([normalized])[0])
        self.invalidate_read_cache("transactions")

    def append_many(self, transactions: list[dict]) -> None:
        """Append validated transactions in one Google Sheets request."""

        if not transactions:
            return
        normalized = [
            normalize_transaction(transaction, generate_missing_id=True)
            for transaction in transactions
        ]
        self._worksheet.append_rows(records_to_sheet_rows(normalized))
        self.invalidate_read_cache("transactions")

    # ==========================================================
    # READ
    # ==========================================================

    def get_transactions(self) -> list[dict]:
        """
        Return all transactions with their Google Sheets row number.
        """

        records = self._read_cached_records(
            "transactions",
            lambda: self._worksheet.get_all_records(default_blank=None),
        )
        return [
            {
                **sheet_record_to_transaction(record),
                "row_number": row_number,
            }
            for row_number, record in enumerate(records, start=2)
        ]

    def get_transactions_dataframe(self) -> pd.DataFrame:
        """
        Return all transactions as normalized DataFrame.
        """

        return pd.DataFrame(self.get_transactions(), columns=[
            *TRANSACTION_FIELDS,
            "row_number",
        ])

    # ==========================================================
    # ACCOUNTS
    # ==========================================================

    def append_account(self, account: dict[str, Any]) -> None:
        """Append a normalized Account record to the Accounts worksheet."""

        normalized = normalize_account_record(account, generate_missing_id=False)
        self._accounts_worksheet.append_row(account_record_to_sheet_row(normalized))
        self.invalidate_read_cache("accounts")

    def get_accounts(self) -> list[dict[str, Any]]:
        """Return normalized Account records with internal physical row metadata."""

        records = self._read_cached_records(
            "accounts",
            lambda: self._accounts_worksheet.get_all_records(default_blank=None),
        )
        return [
            {
                **normalize_account_record(
                    account_sheet_record_to_account(record),
                    generate_missing_id=False,
                ),
                "row_number": row_number,
            }
            for row_number, record in enumerate(records, start=2)
        ]

    def update_account(self, account_id: str, account: dict[str, Any]) -> None:
        """Update one Account by immutable Account ID."""

        normalized = normalize_account_record(account, generate_missing_id=False)
        if normalized["account_id"] != account_id:
            raise ValueError("Account ID cannot be changed.")
        row = self._find_account_row(account_id)
        last_column = self._column_letter(len(ACCOUNT_PHYSICAL_HEADERS))
        self._accounts_worksheet.update(
            f"A{row}:{last_column}{row}",
            [account_record_to_sheet_row(normalized)],
        )
        self.invalidate_read_cache("accounts")

    def delete_account(self, account_id: str) -> None:
        """Delete one Account by immutable Account ID."""

        self._accounts_worksheet.delete_rows(self._find_account_row(account_id))
        self.invalidate_read_cache("accounts")

    # ==========================================================
    # ACCOUNT MOVEMENTS
    # ==========================================================

    def append_account_movement(self, movement: dict[str, Any]) -> None:
        """Append a normalized Transfer or Adjustment record."""

        normalized = normalize_movement(movement)
        self._account_movements_worksheet.append_row(
            movement_record_to_sheet_row(normalized)
        )
        self.invalidate_read_cache("account_movements")

    def get_account_movements(self) -> list[dict[str, Any]]:
        """Return Account Movements with internal physical row metadata."""

        records = self._read_cached_records(
            "account_movements",
            lambda: self._account_movements_worksheet.get_all_records(
                default_blank=None
            ),
        )
        return [
            {
                **normalize_movement(movement_sheet_record_to_movement(record)),
                "row_number": row_number,
            }
            for row_number, record in enumerate(records, start=2)
        ]

    def delete_account_movement(self, movement_id: str) -> None:
        """Delete one Account Movement by immutable Movement ID."""

        self._account_movements_worksheet.delete_rows(
            self._find_account_movement_row(movement_id)
        )
        self.invalidate_read_cache("account_movements")

    # ==========================================================
    # GOALS V2
    # ==========================================================

    def append_goal(self, goal: dict[str, Any]) -> None:
        """Append a normalized Goal V2 record."""

        self._goals_worksheet.append_row(goal_record_to_sheet_row(normalize_goal(goal)))
        self.invalidate_read_cache("goals")

    def get_goals(self) -> list[dict[str, Any]]:
        """Return Goal V2 records with internal physical row metadata."""

        records = self._read_cached_records(
            "goals",
            lambda: self._goals_worksheet.get_all_records(default_blank=None),
        )
        return [
            {
                **normalize_goal(goal_sheet_record_to_goal(record)),
                "row_number": row_number,
            }
            for row_number, record in enumerate(records, start=2)
        ]

    def update_goal(self, goal_id: str, goal: dict[str, Any]) -> None:
        """Update a Goal while preserving its immutable Goal ID."""

        normalized = normalize_goal(goal)
        if normalized["goal_id"] != goal_id:
            raise ValueError("Goal ID cannot be changed.")
        row = self._find_goal_row(goal_id)
        last_column = self._column_letter(len(GOAL_PHYSICAL_HEADERS))
        self._goals_worksheet.update(
            f"A{row}:{last_column}{row}",
            [goal_record_to_sheet_row(normalized)],
        )
        self.invalidate_read_cache("goals")

    def delete_goal(self, goal_id: str) -> None:
        """Delete a Goal configuration by immutable Goal ID only."""

        self._goals_worksheet.delete_rows(self._find_goal_row(goal_id))
        self.invalidate_read_cache("goals")

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        transaction_id: str,
        transaction: dict,
    ) -> None:
        """
        Update transaction at a specific row.

        The current Google Sheets row is resolved immediately from the
        immutable transaction ID. Physical row numbers are not business IDs.
        """

        normalized = normalize_transaction(transaction, generate_missing_id=False)
        if normalized["transaction_id"] != transaction_id:
            raise ValueError("Transaction ID cannot be changed.")
        row = self._find_transaction_row(transaction_id)
        last_column = self._column_letter(len(PHYSICAL_HEADERS))
        self._worksheet.update(
            f"A{row}:{last_column}{row}",
            records_to_sheet_rows([normalized]),
        )
        self.invalidate_read_cache("transactions")

    # ==========================================================
    # DELETE
    # ==========================================================

    def delete(
        self,
        transaction_id: str,
    ) -> None:
        """
        Delete a transaction by its immutable transaction ID.
        """

        self._worksheet.delete_rows(self._find_transaction_row(transaction_id))
        self.invalidate_read_cache("transactions")

    # ==========================================================
    # UTILITIES
    # ==========================================================

    @classmethod
    def invalidate_read_cache(cls, *datasets: str) -> None:
        """Invalidate selected worksheet snapshots after a successful mutation.

        Calling this method never performs a remote read. The next consumer of
        a dataset obtains a fresh snapshot, while unrelated datasets stay warm.
        """

        target_datasets = datasets or cls._DATASETS
        invalid = set(target_datasets).difference(cls._DATASETS)
        if invalid:
            raise ValueError(f"Unknown worksheet cache dataset(s): {sorted(invalid)}")
        with cls._cache_lock:
            for dataset in target_datasets:
                cls._read_cache.pop(dataset, None)

    @classmethod
    def get_dataset_loaded_at(cls, dataset: str) -> datetime | None:
        """Return the source-read timestamp for one cached worksheet dataset."""

        with cls._cache_lock:
            snapshot = cls._read_cache.get(dataset)
            return snapshot.loaded_at if snapshot else None

    @classmethod
    def get_read_cache_status(cls) -> dict[str, dict[str, object]]:
        """Expose small, non-financial cache diagnostics for dashboard UI/tests."""

        with cls._cache_lock:
            return {
                dataset: {
                    "loaded_at": snapshot.loaded_at,
                    "is_stale": snapshot.is_stale,
                    "warning": snapshot.warning,
                    **cls._read_metrics[dataset],
                }
                for dataset in cls._DATASETS
                if (snapshot := cls._read_cache.get(dataset)) is not None
            }

    @classmethod
    def reset_read_cache_for_testing(cls) -> None:
        """Clear process snapshots and instrumentation for isolated tests only."""

        with cls._cache_lock:
            cls._read_cache.clear()
            cls._read_metrics = {
                dataset: {"remote_reads": 0, "cache_hits": 0}
                for dataset in cls._DATASETS
            }

    def _read_cached_records(
        self,
        dataset: str,
        loader: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Read one worksheet once per TTL with retry and stale fallback.

        A copy is returned on every call so service and dataframe processing
        cannot mutate the shared source snapshot.
        """

        with self._cache_lock:
            snapshot = self._read_cache.get(dataset)
            if snapshot and self._is_snapshot_fresh(snapshot):
                self._read_metrics[dataset]["cache_hits"] += 1
                return copy.deepcopy(snapshot.records)

        try:
            records = self._read_with_retry(dataset, loader)
        except SheetsReadError as error:
            with self._cache_lock:
                snapshot = self._read_cache.get(dataset)
                if snapshot is None:
                    raise
                snapshot.is_stale = True
                snapshot.warning = (
                    "Google Sheets temporarily unavailable. Showing the most "
                    "recently loaded data."
                )
                LOGGER.warning("Using stale %s snapshot after read failure: %s", dataset, error)
                return copy.deepcopy(snapshot.records)

        snapshot = _CachedDataset(copy.deepcopy(records), datetime.now())
        with self._cache_lock:
            self._read_cache[dataset] = snapshot
        return copy.deepcopy(snapshot.records)

    def _read_with_retry(
        self,
        dataset: str,
        loader: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Retry only bounded transient reads, never writes or schema changes."""

        last_error: Exception | None = None
        for attempt in range(self.MAX_READ_ATTEMPTS):
            try:
                with self._cache_lock:
                    self._read_metrics[dataset]["remote_reads"] += 1
                return loader()
            except Exception as error:  # noqa: BLE001 - transport libraries vary.
                last_error = error
                if not self._is_transient_read_error(error):
                    raise SheetsReadError("Unable to read Google Sheets data.") from error
                if attempt == self.MAX_READ_ATTEMPTS - 1:
                    break
                time.sleep(self.RETRY_DELAYS_SECONDS[attempt])

        raise SheetsReadError("Google Sheets is temporarily unavailable.") from last_error

    @classmethod
    def _is_snapshot_fresh(cls, snapshot: _CachedDataset) -> bool:
        """Return whether one successful snapshot remains inside its short TTL."""

        return time.monotonic() - snapshot.loaded_monotonic < cls.CACHE_TTL_SECONDS

    @staticmethod
    def _is_transient_read_error(error: Exception) -> bool:
        """Recognize quota, temporary server, and connection failures safely."""

        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return True
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        message = str(error).lower()
        return any(
            marker in message
            for marker in ("[429]", "quota exceeded", "temporarily unavailable", "timeout")
        )

    def clear(self) -> None:
        """
        Remove all transaction data.
        """

        self.replace_transactions([])

    def replace_transactions(self, transactions: list[dict]) -> None:
        """Safely replace transaction rows while preserving the V2 schema."""

        normalized = [
            normalize_transaction(transaction, generate_missing_id=True)
            for transaction in transactions
        ]
        rows = [list(PHYSICAL_HEADERS), *records_to_sheet_rows(normalized)]
        self._worksheet.clear()
        last_column = self._column_letter(len(PHYSICAL_HEADERS))
        self._worksheet.update(f"A1:{last_column}1", [rows[0]])
        if transactions:
            self._worksheet.append_rows(rows[1:])
        self.invalidate_read_cache("transactions")

    def _ensure_transaction_schema(self) -> None:
        """Backfill V2 transaction identity fields without rewriting legacy rows."""

        headers = list(self._worksheet.row_values(1))
        if not headers:
            last_column = self._column_letter(len(PHYSICAL_HEADERS))
            self._worksheet.update(f"A1:{last_column}1", [list(PHYSICAL_HEADERS)])
            return
        if headers[: len(LEGACY_HEADERS)] != list(LEGACY_HEADERS):
            raise ValueError("Unsupported transaction worksheet header structure.")

        missing_headers = list(PHYSICAL_HEADERS[len(headers):])
        snapshot_created = False
        if missing_headers:
            self._create_migration_snapshot()
            snapshot_created = True
            end_column = self._column_letter(len(headers) + len(missing_headers))
            start_column = self._column_letter(len(headers) + 1)
            self._worksheet.update(
                f"{start_column}1:{end_column}1",
                [missing_headers],
            )
            headers.extend(missing_headers)

        transaction_id_header = SHEET_HEADERS["transaction_id"]
        account_id_header = SHEET_HEADERS["account_id"]
        if transaction_id_header not in headers or account_id_header not in headers:
            raise ValueError("Transaction worksheet is missing required V2 headers.")

        records = self._worksheet.get_all_records(default_blank=None)
        missing_id_rows = [
            index
            for index, record in enumerate(records, start=2)
            if not record.get(transaction_id_header)
        ]
        if not missing_id_rows:
            return

        if not snapshot_created:
            self._create_migration_snapshot()
        before = self._migration_metrics(records)
        id_column = self._column_letter(headers.index(transaction_id_header) + 1)
        values = [
            [record.get(transaction_id_header) or new_transaction_id()]
            for record in records
        ]
        self._worksheet.update(f"{id_column}2:{id_column}{len(records) + 1}", values)
        after_records = self._worksheet.get_all_records(default_blank=None)
        if before != self._migration_metrics(after_records):
            raise RuntimeError("Transaction migration validation failed; no recovery was attempted.")

    def _find_transaction_row(self, transaction_id: str) -> int:
        """Resolve an immutable transaction ID to its current sheet row."""

        for transaction in self.get_transactions():
            if transaction["transaction_id"] == transaction_id:
                return int(transaction["row_number"])
        raise ValueError("Transaction was not found.")

    def _get_or_create_accounts_worksheet(self):
        """Return the Accounts worksheet, creating its schema once when absent."""

        try:
            worksheet = self._spreadsheet.worksheet(ACCOUNTS_WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(
                title=ACCOUNTS_WORKSHEET_NAME,
                rows=1000,
                cols=len(ACCOUNT_PHYSICAL_HEADERS),
            )
        self._ensure_accounts_schema(worksheet)
        return worksheet

    @staticmethod
    def _ensure_accounts_schema(worksheet: Any) -> None:
        """Create or validate the exact, idempotent Accounts worksheet header."""

        headers = list(worksheet.row_values(1))
        if not headers:
            last_column = SheetService._column_letter(len(ACCOUNT_PHYSICAL_HEADERS))
            worksheet.update(
                f"A1:{last_column}1",
                [list(ACCOUNT_PHYSICAL_HEADERS)],
            )
            return
        if headers != list(ACCOUNT_PHYSICAL_HEADERS):
            raise ValueError("Unsupported Accounts worksheet header structure.")

    def _find_account_row(self, account_id: str) -> int:
        """Resolve an immutable Account ID to its current physical row."""

        for account in self.get_accounts():
            if account["account_id"] == account_id:
                return int(account["row_number"])
        raise ValueError("Account was not found.")

    def _get_or_create_account_movements_worksheet(self):
        """Return the movement worksheet, creating its schema only once."""

        try:
            worksheet = self._spreadsheet.worksheet(ACCOUNT_MOVEMENTS_WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(
                title=ACCOUNT_MOVEMENTS_WORKSHEET_NAME,
                rows=1000,
                cols=len(MOVEMENT_PHYSICAL_HEADERS),
            )
        self._ensure_account_movements_schema(worksheet)
        return worksheet

    @staticmethod
    def _ensure_account_movements_schema(worksheet: Any) -> None:
        """Create or validate the exact, idempotent movement header contract."""

        headers = list(worksheet.row_values(1))
        if not headers:
            last_column = SheetService._column_letter(len(MOVEMENT_PHYSICAL_HEADERS))
            worksheet.update(
                f"A1:{last_column}1",
                [list(MOVEMENT_PHYSICAL_HEADERS)],
            )
            return
        if headers != list(MOVEMENT_PHYSICAL_HEADERS):
            raise ValueError("Unsupported Account Movements worksheet header structure.")

    def _find_account_movement_row(self, movement_id: str) -> int:
        """Resolve an immutable Movement ID to its current physical row."""

        for movement in self.get_account_movements():
            if movement["movement_id"] == movement_id:
                return int(movement["row_number"])
        raise ValueError("Account Movement was not found.")

    def _get_or_create_goals_worksheet(self):
        """Return the Goals worksheet, creating its V2 header only once."""

        try:
            worksheet = self._spreadsheet.worksheet(GOALS_WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(
                title=GOALS_WORKSHEET_NAME,
                rows=1000,
                cols=len(GOAL_PHYSICAL_HEADERS),
            )
        self._ensure_goals_schema(worksheet)
        return worksheet

    @staticmethod
    def _ensure_goals_schema(worksheet: Any) -> None:
        """Create or validate the exact, idempotent Goal V2 header contract."""

        headers = list(worksheet.row_values(1))
        if not headers:
            last_column = SheetService._column_letter(len(GOAL_PHYSICAL_HEADERS))
            worksheet.update(
                f"A1:{last_column}1",
                [list(GOAL_PHYSICAL_HEADERS)],
            )
            return
        if headers != list(GOAL_PHYSICAL_HEADERS):
            raise ValueError("Unsupported Goals worksheet header structure.")

    def _find_goal_row(self, goal_id: str) -> int:
        """Resolve an immutable Goal ID to the current physical worksheet row."""

        for goal in self.get_goals():
            if goal["goal_id"] == goal_id:
                return int(goal["row_number"])
        raise ValueError("Goal was not found.")

    def _create_migration_snapshot(self) -> dict[str, Any]:
        """Capture a pre-migration snapshot in memory for this operation only."""

        return {
            "created_at": datetime.now().isoformat(),
            "worksheet": WORKSHEET_NAME,
            "rows": self._worksheet.get_all_values(),
        }

    @staticmethod
    def _migration_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
        """Return values that must remain stable across schema migration."""

        def _amount(value: object) -> int:
            return int(str(value or "0").replace(".", "").replace(",", ""))

        dates = [str(record.get(SHEET_HEADERS["date"], "")) for record in records]
        return {
            "count": len(records),
            "income": sum(
                _amount(record.get(SHEET_HEADERS["amount"]))
                for record in records
                if str(record.get(SHEET_HEADERS["type"], "")).lower() == "income"
            ),
            "expense": sum(
                _amount(record.get(SHEET_HEADERS["amount"]))
                for record in records
                if str(record.get(SHEET_HEADERS["type"], "")).lower() == "expense"
            ),
            "date_range": (min(dates, default=""), max(dates, default="")),
        }

    @staticmethod
    def _column_letter(index: int) -> str:
        """Return an A1 column label for a one-based column index."""

        label = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            label = chr(65 + remainder) + label
        return label

    def worksheet(self):
        """
        Return worksheet instance.
        """

        return self._worksheet
