"""Regression tests for Sprint 8.7E Account Movements."""

from __future__ import annotations

from datetime import date
import unittest

from services.account_movement_schema import (
    MOVEMENT_PHYSICAL_HEADERS,
    is_valid_movement_id,
)
from services.account_movement_service import AccountMovementService
from services.account_service import AccountService
from services.sheet_service import SheetService


class _FakeSheetService:
    """In-memory persistence double for Account and Movement business rules."""

    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, object]] = {}
        self.transactions: list[dict[str, object]] = []
        self.movements: dict[str, dict[str, object]] = {}

    def append_account(self, account: dict[str, object]) -> None:
        self.accounts[str(account["account_id"])] = dict(account)

    def get_accounts(self) -> list[dict[str, object]]:
        return [
            {**account, "row_number": index}
            for index, account in enumerate(self.accounts.values(), start=2)
        ]

    def update_account(self, account_id: str, account: dict[str, object]) -> None:
        self.accounts[account_id] = dict(account)

    def delete_account(self, account_id: str) -> None:
        del self.accounts[account_id]

    def get_transactions(self) -> list[dict[str, object]]:
        return list(self.transactions)

    def append_account_movement(self, movement: dict[str, object]) -> None:
        self.movements[str(movement["movement_id"])] = dict(movement)

    def get_account_movements(self) -> list[dict[str, object]]:
        return [
            {**movement, "row_number": index}
            for index, movement in enumerate(self.movements.values(), start=2)
        ]

    def delete_account_movement(self, movement_id: str) -> None:
        del self.movements[movement_id]


class _FakeMovementsWorksheet:
    """Minimal worksheet fake for idempotent movement header tests."""

    def __init__(self) -> None:
        self.headers: list[str] = []
        self.update_calls = 0

    def row_values(self, row: int) -> list[str]:
        return list(self.headers)

    def update(self, cell_range: str, values: list[list[str]]) -> None:
        self.headers = list(values[0])
        self.update_calls += 1


class AccountMovementTests(unittest.TestCase):
    """Verify Transfer and Adjustment affect only derived Account balances."""

    def setUp(self) -> None:
        self.sheet = _FakeSheetService()
        self.accounts = AccountService(self.sheet)
        self.movements = AccountMovementService(self.sheet)
        self.account_a = self.accounts.create_account(
            account_name="Makan", account_location="DANA", initial_balance=500_000
        )
        self.account_b = self.accounts.create_account(
            account_name="Laptop", account_location="BCA", initial_balance=200_000
        )

    def _transfer(self, amount: int = 100_000):
        return self.movements.create_transfer(
            from_account_id=self.account_a.account_id,
            to_account_id=self.account_b.account_id,
            amount=amount,
            movement_date=date(2026, 8, 21),
            note="allocation",
        )

    def test_transfer_changes_both_balances_and_preserves_total(self) -> None:
        movement = self._transfer()

        self.assertTrue(is_valid_movement_id(movement.movement_id))
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 400_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_b.account_id), 300_000)
        self.assertEqual(
            self.accounts.calculate_current_balance(self.account_a.account_id)
            + self.accounts.calculate_current_balance(self.account_b.account_id),
            700_000,
        )

    def test_transfer_rejects_same_account_and_non_positive_amount(self) -> None:
        with self.assertRaisesRegex(ValueError, "harus berbeda"):
            self.movements.create_transfer(
                from_account_id=self.account_a.account_id,
                to_account_id=self.account_a.account_id,
                amount=10,
                movement_date=date.today(),
            )
        with self.assertRaisesRegex(ValueError, "lebih dari nol"):
            self._transfer(0)

    def test_transfer_can_make_source_balance_negative(self) -> None:
        self._transfer(600_000)

        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), -100_000)
        self.assertEqual(
            self.movements.get_transfer_preview(self.account_a.account_id, 1),
            -100_001,
        )

    def test_adjustment_persists_delta_and_reaches_actual_balance(self) -> None:
        downward = self.movements.create_adjustment(
            account_id=self.account_a.account_id,
            actual_balance=450_000,
            movement_date=date.today(),
            reason="Wallet check",
        )
        self.assertEqual(downward.amount, -50_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 450_000)

        upward = self.movements.create_adjustment(
            account_id=self.account_a.account_id,
            actual_balance=550_000,
            movement_date=date.today(),
            reason="Cash found",
        )
        self.assertEqual(upward.amount, 100_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 550_000)

    def test_adjustment_requires_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "wajib diisi"):
            self.movements.create_adjustment(
                account_id=self.account_a.account_id,
                actual_balance=500_000,
                movement_date=date.today(),
                reason="  ",
            )

    def test_movement_activity_locks_initial_balance_and_account_deletion(self) -> None:
        self._transfer()

        self.assertFalse(self.accounts.is_initial_balance_editable(self.account_a.account_id))
        with self.assertRaisesRegex(ValueError, "tidak dapat dihapus"):
            self.accounts.delete_account(self.account_a.account_id)

    def test_deleting_movements_reverses_their_derived_effects(self) -> None:
        transfer = self._transfer()
        self.movements.delete_movement(transfer.movement_id)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 500_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_b.account_id), 200_000)

        adjustment = self.movements.create_adjustment(
            account_id=self.account_a.account_id,
            actual_balance=450_000,
            movement_date=date.today(),
            reason="reconcile",
        )
        self.movements.delete_movement(adjustment.movement_id)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 500_000)

    def test_archived_accounts_cannot_receive_new_movements_but_history_remains_readable(self) -> None:
        zero_account = self.accounts.create_account(
            account_name="Closed", account_location="Cash", initial_balance=0
        )
        movement = self.movements.create_adjustment(
            account_id=zero_account.account_id,
            actual_balance=0,
            movement_date=date.today(),
            reason="close",
        )
        self.accounts.archive_account(zero_account.account_id)

        with self.assertRaisesRegex(ValueError, "diarsipkan"):
            self.movements.create_adjustment(
                account_id=zero_account.account_id,
                actual_balance=0,
                movement_date=date.today(),
                reason="blocked",
            )
        self.assertIn(movement.movement_id, [item.movement_id for item in self.movements.list_movements()])

    def test_movements_do_not_change_transaction_analytics_or_legacy_null_records(self) -> None:
        self.sheet.transactions.append(
            {"account_id": None, "type": "expense", "amount": 99_000}
        )
        self._transfer()
        self.movements.create_adjustment(
            account_id=self.account_a.account_id,
            actual_balance=450_000,
            movement_date=date.today(),
            reason="reconcile",
        )

        self.assertEqual(len(self.sheet.transactions), 1)
        self.assertEqual(self.sheet.transactions[0]["amount"], 99_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_b.account_id), 300_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 450_000)

    def test_account_movements_schema_initialization_is_idempotent(self) -> None:
        worksheet = _FakeMovementsWorksheet()

        SheetService._ensure_account_movements_schema(worksheet)
        SheetService._ensure_account_movements_schema(worksheet)

        self.assertEqual(worksheet.headers, list(MOVEMENT_PHYSICAL_HEADERS))
        self.assertEqual(worksheet.update_calls, 1)


if __name__ == "__main__":
    unittest.main()
