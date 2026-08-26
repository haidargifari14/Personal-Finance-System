"""Account lifecycle and balance business rules."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Mapping

from models.account import Account
from services.account_schema import new_account_id
from services.sheet_service import SheetService


class AccountService:
    """Manage Accounts while keeping Google Sheets access in SheetService.

    The balance engine combines linked income/expense transactions and Account
    Movements. It never persists a mutable current-balance field.
    """

    def __init__(self, sheet_service: SheetService | None = None) -> None:
        """Initialize the service with an optional persistence dependency."""

        self._sheet_service = sheet_service

    def create_account(
        self,
        *,
        account_name: str,
        account_location: str,
        initial_balance: int | float | str,
        tracking_start_date: date | None = None,
    ) -> Account:
        """Create an active Account with a permanent UUID and initial balance."""

        now = self._now_text()
        record = {
            "account_id": new_account_id(),
            "account_name": self._validate_text(account_name, "Nama akun"),
            "account_location": self._validate_text(
                account_location,
                "Lokasi akun",
            ),
            "initial_balance": self._validate_balance(initial_balance),
            "tracking_start_date": (tracking_start_date or date.today()).isoformat(),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        self._get_sheet_service().append_account(record)
        return Account.from_record(record)

    def list_accounts(self) -> list[Account]:
        """Return all Accounts, including archived Accounts for history."""

        return [
            Account.from_record(record)
            for record in self._get_sheet_service().get_accounts()
        ]

    def list_active_accounts(self) -> list[Account]:
        """Return Accounts that can receive newly created transactions."""

        return [
            account
            for account in self.list_accounts()
            if account.status.strip().lower() == "active"
        ]

    def validate_active_account(self, account_id: str) -> Account:
        """Return an active Account or raise a user-facing validation error."""

        account = self.get_account(account_id)
        if account.status.strip().lower() != "active":
            raise ValueError("Akun yang diarsipkan tidak dapat digunakan untuk transaksi baru.")
        return account

    def get_account_summaries(self) -> list[dict[str, object]]:
        """Return Accounts with service-calculated balances and activity flags."""

        records = self._get_sheet_service().get_accounts()
        balances = {
            str(record["account_id"]): int(record["initial_balance"])
            for record in records
        }
        activity_ids: set[str] = set()
        for transaction in self._get_sheet_service().get_transactions():
            account_id = str(transaction.get("account_id") or "").strip()
            if account_id not in balances:
                continue
            activity_ids.add(account_id)
            amount = self._transaction_amount(transaction)
            transaction_type = str(transaction.get("type", "")).strip().lower()
            if transaction_type == "income":
                balances[account_id] += amount
            elif transaction_type == "expense":
                balances[account_id] -= amount

        for movement in self._get_account_movements():
            self._apply_movement_to_balances(movement, balances, activity_ids)

        return [
            {
                "account": Account.from_record(record),
                "current_balance": balances[str(record["account_id"])],
                "has_activity": str(record["account_id"]) in activity_ids,
            }
            for record in records
        ]

    def get_current_balance_summary(self) -> dict[str, int]:
        """Return the current system balance from active Account summaries only.

        Historical Transactions with a null Account ID remain unavailable to the
        balance engine by design, while Transfers and Adjustments are already
        reflected through each Account's derived current balance.
        """

        active_summaries = [
            summary
            for summary in self.get_account_summaries()
            if str(summary["account"].status).strip().lower() == "active"
        ]
        return {
            "current_balance": sum(
                int(summary["current_balance"])
                for summary in active_summaries
            ),
            "active_account_count": len(active_summaries),
        }

    def get_account(self, account_id: str) -> Account:
        """Return one Account by its immutable Account ID."""

        return Account.from_record(self._get_account_record(account_id))

    def update_account_metadata(
        self,
        account_id: str,
        *,
        account_name: str,
        account_location: str,
    ) -> Account:
        """Update Account name and location without changing financial values."""

        record = self._get_account_record(account_id)
        updated = {
            **record,
            "account_name": self._validate_text(account_name, "Nama akun"),
            "account_location": self._validate_text(
                account_location,
                "Lokasi akun",
            ),
            "updated_at": self._now_text(),
        }
        self._get_sheet_service().update_account(account_id, updated)
        return Account.from_record(updated)

    def update_initial_balance(
        self,
        account_id: str,
        initial_balance: int | float | str,
    ) -> Account:
        """Correct initial balance only before the Account has linked activity."""

        if self.has_activity(account_id):
            raise ValueError(
                "Saldo awal tidak dapat diubah setelah akun memiliki aktivitas."
            )
        record = self._get_account_record(account_id)
        updated = {
            **record,
            "initial_balance": self._validate_balance(initial_balance),
            "updated_at": self._now_text(),
        }
        self._get_sheet_service().update_account(account_id, updated)
        return Account.from_record(updated)

    def calculate_current_balance(self, account_id: str) -> int:
        """Calculate an Account balance from initial and linked transactions.

        Transactions with a missing Account ID are never included. Negative
        balances are valid and deliberately returned unchanged.
        """

        account = self.get_account(account_id)
        income = 0
        expense = 0
        for transaction in self._linked_transactions(account.account_id):
            amount = self._transaction_amount(transaction)
            transaction_type = str(transaction.get("type", "")).strip().lower()
            if transaction_type == "income":
                income += amount
            elif transaction_type == "expense":
                expense += amount
        movement_effect = self._movement_effect_for_account(account.account_id)
        return account.initial_balance + income - expense + movement_effect

    def has_activity(self, account_id: str) -> bool:
        """Return whether currently available sources link activity to an Account."""

        self._get_account_record(account_id)
        return bool(
            self._linked_transactions(account_id)
            or self._linked_movements(account_id)
        )

    def is_initial_balance_editable(self, account_id: str) -> bool:
        """Return whether the Account's initial balance remains correctable."""

        return not self.has_activity(account_id)

    def delete_account(self, account_id: str) -> None:
        """Delete an Account only when no linked activity exists."""

        if self.has_activity(account_id):
            raise ValueError("Akun dengan aktivitas tidak dapat dihapus.")
        self._get_sheet_service().delete_account(account_id)

    def archive_account(self, account_id: str) -> Account:
        """Archive an Account only when its calculated balance equals zero."""

        if self.calculate_current_balance(account_id) != 0:
            raise ValueError(
                "Akun hanya dapat diarsipkan setelah saldo menjadi nol. "
                "Pindahkan atau rekonsiliasi sisa alokasi terlebih dahulu."
            )
        record = self._get_account_record(account_id)
        updated = {
            **record,
            "status": "archived",
            "updated_at": self._now_text(),
        }
        self._get_sheet_service().update_account(account_id, updated)
        return Account.from_record(updated)

    def _get_account_record(self, account_id: str) -> dict[str, Any]:
        """Return one persisted Account record or raise a clear domain error."""

        normalized_id = str(account_id).strip()
        for record in self._get_sheet_service().get_accounts():
            if record["account_id"] == normalized_id:
                return {
                    key: value
                    for key, value in record.items()
                    if key != "row_number"
                }
        raise ValueError("Akun tidak ditemukan.")

    def _linked_transactions(self, account_id: str) -> list[Mapping[str, Any]]:
        """Return only transactions explicitly linked to the requested Account."""

        return [
            transaction
            for transaction in self._get_sheet_service().get_transactions()
            if str(transaction.get("account_id") or "").strip() == account_id
        ]

    def _linked_movements(self, account_id: str) -> list[Mapping[str, Any]]:
        """Return Transfer or Adjustment records that reference an Account."""

        return [
            movement
            for movement in self._get_account_movements()
            if account_id in {
                str(movement.get("from_account_id") or "").strip(),
                str(movement.get("to_account_id") or "").strip(),
                str(movement.get("account_id") or "").strip(),
            }
        ]

    def _get_account_movements(self) -> list[Mapping[str, Any]]:
        """Return persisted movements, supporting pre-movement test doubles."""

        get_movements = getattr(self._get_sheet_service(), "get_account_movements", None)
        return list(get_movements()) if callable(get_movements) else []

    def _movement_effect_for_account(self, account_id: str) -> int:
        """Calculate the net movement effect for one Account identity."""

        effect = 0
        for movement in self._linked_movements(account_id):
            amount = self._transaction_amount(movement)
            movement_type = str(movement.get("movement_type") or "").lower()
            if movement_type == "transfer":
                if str(movement.get("from_account_id") or "").strip() == account_id:
                    effect -= amount
                if str(movement.get("to_account_id") or "").strip() == account_id:
                    effect += amount
            elif movement_type == "adjustment":
                if str(movement.get("account_id") or "").strip() == account_id:
                    effect += amount
        return effect

    @classmethod
    def _apply_movement_to_balances(
        cls,
        movement: Mapping[str, Any],
        balances: dict[str, int],
        activity_ids: set[str],
    ) -> None:
        """Apply a persisted movement once to batch Account summaries."""

        movement_type = str(movement.get("movement_type") or "").lower()
        amount = cls._transaction_amount(movement)
        if movement_type == "transfer":
            source = str(movement.get("from_account_id") or "").strip()
            destination = str(movement.get("to_account_id") or "").strip()
            if source in balances:
                balances[source] -= amount
                activity_ids.add(source)
            if destination in balances:
                balances[destination] += amount
                activity_ids.add(destination)
        elif movement_type == "adjustment":
            account_id = str(movement.get("account_id") or "").strip()
            if account_id in balances:
                balances[account_id] += amount
                activity_ids.add(account_id)

    def _get_sheet_service(self) -> SheetService:
        """Return the lazily created Sheets repository dependency."""

        if self._sheet_service is None:
            self._sheet_service = SheetService()
        return self._sheet_service

    @staticmethod
    def _validate_text(value: str, label: str) -> str:
        """Validate a required Account metadata field."""

        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{label} wajib diisi.")
        return normalized

    @staticmethod
    def _validate_balance(value: int | float | str) -> int:
        """Validate a whole-number balance without clamping negative values."""

        if isinstance(value, bool):
            raise ValueError("Saldo awal harus berupa angka.")
        if isinstance(value, float):
            if not isfinite(value) or not value.is_integer():
                raise ValueError("Saldo awal harus berupa angka bulat.")
            return int(value)
        try:
            return int(str(value).strip().replace(".", "").replace(",", ""))
        except (TypeError, ValueError) as error:
            raise ValueError("Saldo awal harus berupa angka.") from error

    @staticmethod
    def _transaction_amount(transaction: Mapping[str, Any]) -> int:
        """Normalize a persisted transaction amount for balance calculation."""

        return int(
            str(transaction.get("amount", 0) or 0)
            .replace(".", "")
            .replace(",", "")
            .replace(" ", "")
        )

    @staticmethod
    def _now_text() -> str:
        """Return a local application timestamp for Account metadata."""

        return datetime.now().isoformat(timespec="seconds")
