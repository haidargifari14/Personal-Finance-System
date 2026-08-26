"""Central schema contract for the Account Movements Google Sheets worksheet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
from uuid import UUID, uuid4


MOVEMENT_FIELDS = (
    "movement_id",
    "date",
    "movement_type",
    "from_account_id",
    "to_account_id",
    "account_id",
    "amount",
    "note",
    "created_at",
    "updated_at",
)
MOVEMENT_HEADERS = {
    "movement_id": "Movement ID",
    "date": "Date",
    "movement_type": "Movement Type",
    "from_account_id": "From Account ID",
    "to_account_id": "To Account ID",
    "account_id": "Account ID",
    "amount": "Amount",
    "note": "Note / Reason",
    "created_at": "Created At",
    "updated_at": "Updated At",
}
MOVEMENT_PHYSICAL_HEADERS = tuple(MOVEMENT_HEADERS[field] for field in MOVEMENT_FIELDS)
MOVEMENT_TYPES = ("transfer", "adjustment")


def new_movement_id() -> str:
    """Return a collision-safe immutable Account Movement identifier."""

    return str(uuid4())


def is_valid_movement_id(value: object) -> bool:
    """Return whether *value* is a UUID Account Movement identifier."""

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        UUID(value.strip())
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def normalize_movement(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one persisted movement using the centralized field contract."""

    movement_id = str(record.get("movement_id") or "").strip()
    if not is_valid_movement_id(movement_id):
        raise ValueError("Movement ID is invalid.")
    movement_type = str(record.get("movement_type") or "").strip().lower()
    if movement_type not in MOVEMENT_TYPES:
        raise ValueError("Movement type is invalid.")
    return {
        "movement_id": movement_id,
        "date": _normalize_date(record.get("date")),
        "movement_type": movement_type,
        "from_account_id": _normalize_optional_id(record.get("from_account_id")),
        "to_account_id": _normalize_optional_id(record.get("to_account_id")),
        "account_id": _normalize_optional_id(record.get("account_id")),
        "amount": int(record.get("amount", 0)),
        "note": str(record.get("note") or "").strip(),
        "created_at": _normalize_datetime(record.get("created_at")),
        "updated_at": _normalize_datetime(record.get("updated_at")),
    }


def movement_record_to_sheet_row(record: Mapping[str, Any]) -> list[Any]:
    """Return one movement in the physical Google Sheets column order."""

    return ["" if record.get(field) is None else record.get(field, "") for field in MOVEMENT_FIELDS]


def movement_sheet_record_to_movement(record: Mapping[str, Any]) -> dict[str, Any]:
    """Map physical Google Sheets headers to internal movement fields."""

    return {field: record.get(header) for field, header in MOVEMENT_HEADERS.items()}


def _normalize_optional_id(value: object) -> str | None:
    """Normalize nullable relationship IDs without replacing their identity."""

    normalized = str(value or "").strip()
    return normalized or None


def _normalize_date(value: object) -> str:
    """Return an ISO date string for a date-like persisted value."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _normalize_datetime(value: object) -> str:
    """Return a normalized timestamp string without imposing timezone policy."""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value or "").strip()
