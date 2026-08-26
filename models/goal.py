"""Goal V2 domain model linked to an Account allocation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Goal:
    """Persisted Goal configuration; financial progress is never stored here."""

    goal_id: str
    account_id: str
    target_amount: int
    deadline: str | None
    priority: str
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, record: dict[str, object]) -> "Goal":
        """Build a Goal from one normalized persistence record."""

        deadline = str(record.get("deadline") or "").strip() or None
        return cls(
            goal_id=str(record["goal_id"]),
            account_id=str(record["account_id"]),
            target_amount=int(record["target_amount"]),
            deadline=deadline,
            priority=str(record["priority"]),
            status=str(record["status"]),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )
