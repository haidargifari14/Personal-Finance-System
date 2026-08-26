"""Regression tests for the Sprint 8.7C Account foundation."""

from __future__ import annotations

import unittest

from services.account_schema import ACCOUNT_PHYSICAL_HEADERS, is_valid_account_id
from services.account_service import AccountService
from services.sheet_service import SheetService


class _FakeSheetService:
    """In-memory SheetService substitute for Account business-rule tests."""

    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, object]] = {}
        self.transactions: list[dict[str, object]] = []

    def append_account(self, account: dict[str, object]) -> None:
        self.accounts[str(account["account_id"])] = dict(account)

    def get_accounts(self) -> list[dict[str, object]]:
        return [
            {**record, "row_number": index}
            for index, record in enumerate(self.accounts.values(), start=2)
        ]

    def update_account(self, account_id: str, account: dict[str, object]) -> None:
        if account_id not in self.accounts:
            raise ValueError("Account was not found.")
        self.accounts[account_id] = dict(account)

    def delete_account(self, account_id: str) -> None:
        del self.accounts[account_id]

    def get_transactions(self) -> list[dict[str, object]]:
        return list(self.transactions)


class _FakeAccountsWorksheet:
    """Minimal worksheet fake for Accounts header initialization tests."""

    def __init__(self) -> None:
        self.headers: list[str] = []
        self.update_calls = 0

    def row_values(self, row: int) -> list[str]:
        return list(self.headers)

    def update(self, cell_range: str, values: list[list[str]]) -> None:
        self.update_calls += 1
        self.headers = list(values[0])


class AccountServiceTests(unittest.TestCase):
    """Verify Account persistence-facing lifecycle and balance behavior."""

    def setUp(self) -> None:
        self.sheet_service = _FakeSheetService()
        self.service = AccountService(self.sheet_service)

    def _create_account(self, initial_balance: int = 1_000):
        return self.service.create_account(
            account_name="Daily Fund",
            account_location="DANA",
            initial_balance=initial_balance,
        )

    def _add_activity(
        self,
        account_id: str | None,
        transaction_type: str = "expense",
        amount: int = 100,
    ) -> None:
        self.sheet_service.transactions.append(
            {
                "account_id": account_id,
                "type": transaction_type,
                "amount": amount,
            }
        )

    def test_new_account_balance_equals_its_initial_balance(self) -> None:
        account = self._create_account(1_250)

        self.assertEqual(self.service.calculate_current_balance(account.account_id), 1_250)
        self.assertEqual(account.status, "active")
        self.assertTrue(is_valid_account_id(account.account_id))

    def test_current_balance_summary_uses_active_account_balances(self) -> None:
        """Overview can obtain a date-independent current Account balance."""

        active = self._create_account(1_000)
        archived = self._create_account(500)
        self.sheet_service.accounts[archived.account_id]["status"] = "archived"
        self._add_activity(active.account_id, "income", 250)

        summary = self.service.get_current_balance_summary()

        self.assertEqual(summary["current_balance"], 1_250)
        self.assertEqual(summary["active_account_count"], 1)

    def test_account_id_remains_immutable_after_metadata_edit(self) -> None:
        account = self._create_account()

        updated = self.service.update_account_metadata(
            account.account_id,
            account_name="Daily Expenses",
            account_location="BCA",
        )

        self.assertEqual(updated.account_id, account.account_id)

    def test_metadata_edit_does_not_change_balance(self) -> None:
        account = self._create_account(500)

        self.service.update_account_metadata(
            account.account_id,
            account_name="Renamed",
            account_location="Cash",
        )

        self.assertEqual(self.service.calculate_current_balance(account.account_id), 500)

    def test_initial_balance_can_be_edited_before_activity(self) -> None:
        account = self._create_account(500)

        updated = self.service.update_initial_balance(account.account_id, 750)

        self.assertEqual(updated.initial_balance, 750)
        self.assertEqual(self.service.calculate_current_balance(account.account_id), 750)

    def test_initial_balance_cannot_be_edited_after_activity(self) -> None:
        account = self._create_account()
        self._add_activity(account.account_id)

        with self.assertRaisesRegex(ValueError, "tidak dapat diubah"):
            self.service.update_initial_balance(account.account_id, 750)

    def test_empty_account_can_be_deleted(self) -> None:
        account = self._create_account()

        self.service.delete_account(account.account_id)

        self.assertEqual(self.service.list_accounts(), [])

    def test_account_with_activity_cannot_be_deleted(self) -> None:
        account = self._create_account()
        self._add_activity(account.account_id)

        with self.assertRaisesRegex(ValueError, "tidak dapat dihapus"):
            self.service.delete_account(account.account_id)

    def test_zero_balance_account_can_be_archived(self) -> None:
        account = self._create_account(0)

        archived = self.service.archive_account(account.account_id)

        self.assertEqual(archived.status, "archived")
        self.assertEqual(self.service.get_account(account.account_id).status, "archived")

    def test_nonzero_balance_account_cannot_be_archived(self) -> None:
        account = self._create_account(1)

        with self.assertRaisesRegex(ValueError, "saldo menjadi nol"):
            self.service.archive_account(account.account_id)

    def test_negative_balance_is_allowed(self) -> None:
        account = self._create_account(0)
        self._add_activity(account.account_id, "expense", 250)

        self.assertEqual(self.service.calculate_current_balance(account.account_id), -250)

    def test_historical_null_account_transactions_do_not_affect_balance(self) -> None:
        account = self._create_account(500)
        self._add_activity(None, "expense", 400)
        self._add_activity("another-account", "income", 900)

        self.assertEqual(self.service.calculate_current_balance(account.account_id), 500)

    def test_balance_uses_only_linked_income_and_expense_transactions(self) -> None:
        account = self._create_account(1_000)
        self._add_activity(account.account_id, "income", 500)
        self._add_activity(account.account_id, "expense", 200)

        self.assertEqual(self.service.calculate_current_balance(account.account_id), 1_300)

    def test_account_summaries_expose_service_calculated_ui_values(self) -> None:
        account = self._create_account(200)
        self._add_activity(account.account_id, "expense", 50)

        summaries = self.service.get_account_summaries()

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["account"].account_id, account.account_id)
        self.assertEqual(summaries[0]["current_balance"], 150)
        self.assertTrue(summaries[0]["has_activity"])
        self.assertFalse(self.service.is_initial_balance_editable(account.account_id))

    def test_accounts_worksheet_initialization_is_idempotent(self) -> None:
        worksheet = _FakeAccountsWorksheet()

        SheetService._ensure_accounts_schema(worksheet)
        SheetService._ensure_accounts_schema(worksheet)

        self.assertEqual(worksheet.headers, list(ACCOUNT_PHYSICAL_HEADERS))
        self.assertEqual(worksheet.update_calls, 1)


if __name__ == "__main__":
    unittest.main()
