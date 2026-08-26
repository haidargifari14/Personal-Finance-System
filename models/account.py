"""Account domain model used by the Account service layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Account:
    """Immutable representation of persisted Account metadata."""

    account_id: str
    account_name: str
    account_location: str
    initial_balance: int
    tracking_start_date: str
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, record: dict[str, object]) -> "Account":
        """Build an Account model from a normalized persistence record."""

        return cls(
            account_id=str(record["account_id"]),
            account_name=str(record["account_name"]),
            account_location=str(record["account_location"]),
            initial_balance=int(record["initial_balance"]),
            tracking_start_date=str(record["tracking_start_date"]),
            status=str(record["status"]),
            created_at=str(record["created_at"]),
            updated_at=str(record["updated_at"]),
        )

    def to_record(self) -> dict[str, object]:
        """Return the Account in the internal persistence format."""

        return {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "account_location": self.account_location,
            "initial_balance": self.initial_balance,
            "tracking_start_date": self.tracking_start_date,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
