"""Business rules for Account Transfers and Adjustments."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from models.account_movement import AccountMovement
from services.account_movement_schema import new_movement_id
from services.account_service import AccountService
from services.sheet_service import SheetService


class AccountMovementService:
    """Create, list, and delete non-transaction Account balance movements."""

    def __init__(self, sheet_service: SheetService | None = None) -> None:
        """Initialize the service with an optional persistence dependency."""

        self._sheet_service = sheet_service
        self._account_service = AccountService(self._get_sheet_service())

    def create_transfer(
        self,
        *,
        from_account_id: str,
        to_account_id: str,
        amount: int | float | str,
        movement_date: date | None,
        note: str | None = None,
    ) -> AccountMovement:
        """Persist a Transfer between two distinct active Accounts.

        A source Account may become negative. Its balance remains derived by
        ``AccountService`` after this record is saved.
        """

        source = self._account_service.validate_active_account(from_account_id)
        destination = self._account_service.validate_active_account(to_account_id)
        if source.account_id == destination.account_id:
            raise ValueError("Akun asal dan tujuan transfer harus berbeda.")
        record = self._base_record(
            movement_type="transfer",
            movement_date=movement_date,
            amount=self._validate_positive_amount(amount),
            note=(note or "").strip(),
        )
        record.update(
            from_account_id=source.account_id,
            to_account_id=destination.account_id,
            account_id=None,
        )
        self._get_sheet_service().append_account_movement(record)
        return AccountMovement.from_record(record)

    def create_adjustment(
        self,
        *,
        account_id: str,
        actual_balance: int | float | str,
        movement_date: date | None,
        reason: str,
    ) -> AccountMovement:
        """Persist the delta needed to reconcile an Account to its actual balance."""

        account = self._account_service.validate_active_account(account_id)
        normalized_reason = str(reason or "").strip()
        if not normalized_reason:
            raise ValueError("Alasan penyesuaian wajib diisi.")
        actual = self._validate_signed_amount(actual_balance, "Saldo aktual")
        current = self._account_service.calculate_current_balance(account.account_id)
        record = self._base_record(
            movement_type="adjustment",
            movement_date=movement_date,
            amount=actual - current,
            note=normalized_reason,
        )
        record.update(
            from_account_id=None,
            to_account_id=None,
            account_id=account.account_id,
        )
        self._get_sheet_service().append_account_movement(record)
        return AccountMovement.from_record(record)

    def list_movements(self) -> list[AccountMovement]:
        """Return all persisted Account Movements, newest first."""

        movements = [
            AccountMovement.from_record(record)
            for record in self._get_sheet_service().get_account_movements()
        ]
        return sorted(
            movements,
            key=lambda movement: (movement.date, movement.created_at, movement.movement_id),
            reverse=True,
        )

    def delete_movement(self, movement_id: str) -> None:
        """Delete a Movement by immutable ID; derived balances then recalculate."""

        self._get_sheet_service().delete_account_movement(str(movement_id).strip())

    def get_transfer_preview(
        self,
        from_account_id: str,
        amount: int | float | str,
    ) -> int:
        """Return the projected source balance for a pre-confirmation warning."""

        self._account_service.validate_active_account(from_account_id)
        return (
            self._account_service.calculate_current_balance(from_account_id)
            - self._validate_positive_amount(amount)
        )

    def get_adjustment_preview(
        self,
        account_id: str,
        actual_balance: int | float | str,
    ) -> tuple[int, int]:
        """Return the current balance and resulting adjustment delta for UI review."""

        account = self._account_service.validate_active_account(account_id)
        current = self._account_service.calculate_current_balance(account.account_id)
        actual = self._validate_signed_amount(actual_balance, "Saldo aktual")
        return current, actual - current

    @staticmethod
    def _base_record(
        *,
        movement_type: str,
        movement_date: date | None,
        amount: int,
        note: str,
    ) -> dict[str, object]:
        """Create immutable metadata shared by Transfer and Adjustment records."""

        if movement_date is None:
            raise ValueError("Tanggal pergerakan akun wajib dipilih.")
        now = datetime.now().isoformat(timespec="seconds")
        return {
            "movement_id": new_movement_id(),
            "date": movement_date.isoformat(),
            "movement_type": movement_type,
            "amount": amount,
            "note": note,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _validate_positive_amount(value: int | float | str) -> int:
        """Validate a strictly positive whole-number transfer amount."""

        amount = AccountMovementService._validate_signed_amount(value, "Nominal transfer")
        if amount <= 0:
            raise ValueError("Nominal transfer harus lebih dari nol.")
        return amount

    @staticmethod
    def _validate_signed_amount(value: int | float | str, label: str) -> int:
        """Validate a whole-number balance or amount without clamping negatives."""

        if isinstance(value, bool):
            raise ValueError(f"{label} harus berupa angka.")
        if isinstance(value, float):
            if not isfinite(value) or not value.is_integer():
                raise ValueError(f"{label} harus berupa angka bulat.")
            return int(value)
        try:
            return int(str(value).strip().replace(".", "").replace(",", ""))
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} harus berupa angka.") from error

    def _get_sheet_service(self) -> SheetService:
        """Return the lazily initialized persistence dependency."""

        if self._sheet_service is None:
            self._sheet_service = SheetService()
        return self._sheet_service
