"""Immutable Account Movement domain model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountMovement:
    """Represent one persisted Transfer or Adjustment."""

    movement_id: str
    date: str
    movement_type: str
    from_account_id: str | None
    to_account_id: str | None
    account_id: str | None
    amount: int
    note: str
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, record: dict[str, object]) -> "AccountMovement":
        """Build a Movement model from a normalized persistence record."""

        return cls(
            movement_id=str(record["movement_id"]),
            date=str(record["date"]),
            movement_type=str(record["movement_type"]),
            from_account_id=_optional_text(record.get("from_account_id")),
            to_account_id=_optional_text(record.get("to_account_id")),
            account_id=_optional_text(record.get("account_id")),
            amount=int(record["amount"]),
            note=str(record["note"]),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )


def _optional_text(value: object) -> str | None:
    """Convert an optional persisted value to trimmed text or ``None``."""

    normalized = str(value or "").strip()
    return normalized or None
