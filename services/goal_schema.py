"""Central schema contract for the Goal V2 Google Sheets worksheet."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
from uuid import UUID, uuid4


GOAL_FIELDS = (
    "goal_id",
    "account_id",
    "target_amount",
    "deadline",
    "priority",
    "status",
    "created_at",
    "updated_at",
)
GOAL_HEADERS = {
    "goal_id": "Goal ID",
    "account_id": "Account ID",
    "target_amount": "Target Amount",
    "deadline": "Deadline",
    "priority": "Priority",
    "status": "Status",
    "created_at": "Created At",
    "updated_at": "Updated At",
}
GOAL_PHYSICAL_HEADERS = tuple(GOAL_HEADERS[field] for field in GOAL_FIELDS)
GOAL_PRIORITIES = ("high", "medium", "low")
GOAL_STATUSES = ("active", "paused", "closed")


def new_goal_id() -> str:
    """Return a collision-safe immutable Goal V2 identifier."""

    return str(uuid4())


def is_valid_goal_id(value: object) -> bool:
    """Return whether a value is a valid UUID Goal identifier."""

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        UUID(value.strip())
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def normalize_goal(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Goal record using the centralized physical schema contract."""

    goal_id = str(record.get("goal_id") or "").strip()
    if not is_valid_goal_id(goal_id):
        raise ValueError("Goal ID is invalid.")
    account_id = str(record.get("account_id") or "").strip()
    if not account_id:
        raise ValueError("Account ID is required.")
    priority = str(record.get("priority") or "").strip().lower()
    if priority not in GOAL_PRIORITIES:
        raise ValueError("Goal priority is invalid.")
    status = str(record.get("status") or "").strip().lower()
    if status not in GOAL_STATUSES:
        raise ValueError("Goal status is invalid.")
    return {
        "goal_id": goal_id,
        "account_id": account_id,
        "target_amount": int(record.get("target_amount", 0)),
        "deadline": _normalize_optional_date(record.get("deadline")),
        "priority": priority,
        "status": status,
        "created_at": _normalize_datetime(record.get("created_at")),
        "updated_at": _normalize_datetime(record.get("updated_at")),
    }


def goal_record_to_sheet_row(record: Mapping[str, Any]) -> list[Any]:
    """Return a Goal record in the exact worksheet column order."""

    return ["" if record.get(field) is None else record.get(field, "") for field in GOAL_FIELDS]


def goal_sheet_record_to_goal(record: Mapping[str, Any]) -> dict[str, Any]:
    """Map physical Goal headers to their internal field names."""

    return {field: record.get(header) for field, header in GOAL_HEADERS.items()}


def _normalize_optional_date(value: object) -> str | None:
    """Normalize an optional deadline to ISO format without inventing one."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() or None


def _normalize_datetime(value: object) -> str:
    """Normalize timestamps without imposing a timezone policy."""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value or "").strip()
