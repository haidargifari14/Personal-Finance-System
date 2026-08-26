"""Central schema contract for the Accounts Google Sheets worksheet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping
from uuid import UUID, uuid4

ACCOUNT_FIELDS = (
    "account_id",
    "account_name",
    "account_location",
    "initial_balance",
    "tracking_start_date",
    "status",
    "created_at",
    "updated_at",
)

ACCOUNT_HEADERS = {
    "account_id": "Account ID",
    "account_name": "Account Name",
    "account_location": "Account Location",
    "initial_balance": "Initial Balance",
    "tracking_start_date": "Tracking Start Date",
    "status": "Status",
    "created_at": "Created At",
    "updated_at": "Updated At",
}

ACCOUNT_PHYSICAL_HEADERS = tuple(ACCOUNT_HEADERS[field] for field in ACCOUNT_FIELDS)
ACCOUNT_STATUSES = ("active", "archived")


def new_account_id() -> str:
    """Return a collision-safe immutable Account ID."""

    return str(uuid4())


def is_valid_account_id(value: object) -> bool:
    """Return whether a value is a valid UUID Account ID."""

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        UUID(value.strip())
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def normalize_account_record(
    record: Mapping[str, Any],
    *,
    generate_missing_id: bool,
) -> dict[str, Any]:
    """Return an Account record in the centralized internal field order."""

    account_id = record.get("account_id")
    if account_id in (None, ""):
        if not generate_missing_id:
            raise ValueError("Account ID is required.")
        account_id = new_account_id()
    account_id = str(account_id).strip()
    if not is_valid_account_id(account_id):
        raise ValueError("Account ID is invalid.")

    status = str(record.get("status", "active")).strip().lower()
    if status not in ACCOUNT_STATUSES:
        raise ValueError("Account status is invalid.")

    return {
        "account_id": account_id,
        "account_name": str(record.get("account_name", "")).strip(),
        "account_location": str(record.get("account_location", "")).strip(),
        "initial_balance": int(record.get("initial_balance", 0)),
        "tracking_start_date": _normalize_date(record.get("tracking_start_date")),
        "status": status,
        "created_at": _normalize_datetime(record.get("created_at")),
        "updated_at": _normalize_datetime(record.get("updated_at")),
    }


def account_record_to_sheet_row(record: Mapping[str, Any]) -> list[Any]:
    """Return an Account record in the physical Google Sheets column order."""

    return [record.get(field, "") for field in ACCOUNT_FIELDS]


def account_sheet_record_to_account(record: Mapping[str, Any]) -> dict[str, Any]:
    """Map Accounts worksheet headers to internal Account field names."""

    return {
        field: record.get(header)
        for field, header in ACCOUNT_HEADERS.items()
    }


def account_records_to_sheet_rows(records: Iterable[Mapping[str, Any]]) -> list[list[Any]]:
    """Return multiple Account records in physical sheet order."""

    return [account_record_to_sheet_row(record) for record in records]


def _normalize_date(value: object) -> str:
    """Normalize a date-like value to the application's ISO date format."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _normalize_datetime(value: object) -> str:
    """Normalize a timestamp-like value without imposing a timezone policy."""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value or "").strip()
