"""Regression tests for Sprint 8.7D Transaction-to-Account integration."""

from __future__ import annotations

from datetime import date
import unittest

from services.account_service import AccountService
from services.finance_service import FinanceService


class _FakeSheetService:
    """In-memory persistence double shared by Finance and Account services."""

    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, object]] = {}
        self.transactions: dict[str, dict[str, object]] = {}

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

    def append(self, transaction: dict[str, object]) -> None:
        self.transactions[str(transaction["transaction_id"])] = dict(transaction)

    def update(self, transaction_id: str, transaction: dict[str, object]) -> None:
        self.transactions[transaction_id] = dict(transaction)

    def delete(self, transaction_id: str) -> None:
        del self.transactions[transaction_id]

    def get_transactions(self) -> list[dict[str, object]]:
        return list(self.transactions.values())


class TransactionAccountIntegrationTests(unittest.TestCase):
    """Verify linked transaction effects are derived from persisted records."""

    def setUp(self) -> None:
        self.sheet_service = _FakeSheetService()
        self.accounts = AccountService(self.sheet_service)
        self.finance = FinanceService(self.sheet_service)
        self.account_a = self.accounts.create_account(
            account_name="Daily", account_location="DANA", initial_balance=500_000
        )
        self.account_b = self.accounts.create_account(
            account_name="Reserve", account_location="BCA", initial_balance=300_000
        )

    def _save(
        self,
        transaction_type: str,
        amount: int,
        account_id: str | None = None,
    ) -> dict[str, object]:
        return self.finance.save_transaction(
            transaction_date=date(2026, 8, 21),
            transaction_type=transaction_type,
            category="Gaji" if transaction_type == "income" else "Makan",
            amount=amount,
            note="test",
            account_id=account_id or self.account_a.account_id,
        )

    def test_linked_income_and_expense_change_derived_balance(self) -> None:
        income = self._save("income", 100_000)
        self._save("expense", 50_000)

        self.assertEqual(income["account_id"], self.account_a.account_id)
        self.assertNotEqual(income["account_id"], self.account_a.account_name)
        self.assertEqual(
            self.accounts.calculate_current_balance(self.account_a.account_id),
            550_000,
        )

    def test_telegram_style_save_defaults_to_today_with_account(self) -> None:
        transaction = self.finance.save_transaction(
            transaction_date=None,
            transaction_type="expense",
            category="Makan",
            amount=25_000,
            note="Telegram flow",
            account_id=self.account_a.account_id,
        )

        self.assertEqual(transaction["date"], date.today().isoformat())
        self.assertEqual(transaction["account_id"], self.account_a.account_id)

    def test_new_transaction_requires_existing_active_account(self) -> None:
        with self.assertRaisesRegex(ValueError, "Akun wajib dipilih"):
            self.finance.save_transaction(
                transaction_date=date.today(), transaction_type="expense",
                category="Makan", amount=10_000, note="", account_id=None,
            )
        with self.assertRaisesRegex(ValueError, "Akun tidak ditemukan"):
            self._save("expense", 10_000, "missing-account")

    def test_archived_account_cannot_receive_new_transaction(self) -> None:
        self.accounts.update_initial_balance(self.account_b.account_id, 0)
        self.accounts.archive_account(self.account_b.account_id)

        with self.assertRaisesRegex(ValueError, "diarsipkan"):
            self._save("income", 10_000, self.account_b.account_id)

    def test_edit_amount_link_and_type_recalculate_without_double_counting(self) -> None:
        transaction = self._save("expense", 100_000)
        transaction_id = str(transaction["transaction_id"])

        self.finance.update_transaction(
            transaction_id, transaction_date=date.today(), transaction_type="expense",
            category="Makan", amount=150_000, note="edited",
            account_id=self.account_a.account_id,
        )
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 350_000)

        self.finance.update_transaction(
            transaction_id, transaction_date=date.today(), transaction_type="expense",
            category="Makan", amount=150_000, note="moved",
            account_id=self.account_b.account_id,
        )
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 500_000)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_b.account_id), 150_000)

        self.finance.update_transaction(
            transaction_id, transaction_date=date.today(), transaction_type="income",
            category="Gaji", amount=150_000, note="changed type",
            account_id=self.account_b.account_id,
        )
        self.assertEqual(self.accounts.calculate_current_balance(self.account_b.account_id), 450_000)
        self.assertEqual(self.sheet_service.transactions[transaction_id]["transaction_id"], transaction_id)

    def test_edit_date_category_and_note_preserves_identity_and_balance(self) -> None:
        """Metadata edits must not create a second transaction balance effect."""

        transaction = self._save("expense", 100_000)
        transaction_id = str(transaction["transaction_id"])

        self.finance.update_transaction(
            transaction_id,
            transaction_date=date(2026, 8, 24),
            transaction_type="expense",
            category="Tempat Tinggal",
            amount=100_000,
            note="Updated date, category, and note",
            account_id=self.account_a.account_id,
        )

        persisted = self.sheet_service.transactions[transaction_id]
        self.assertEqual(persisted["transaction_id"], transaction_id)
        self.assertEqual(persisted["date"], "2026-08-24")
        self.assertEqual(persisted["category"], "Tempat Tinggal")
        self.assertEqual(persisted["note"], "Updated date, category, and note")
        self.assertEqual(
            self.accounts.calculate_current_balance(self.account_a.account_id),
            400_000,
        )

    def test_classification_edit_preserves_actual_account_balance(self) -> None:
        """Periodic metadata must not alter the linked cash outflow."""

        transaction = self._save("expense", 16_000_000)
        transaction_id = str(transaction["transaction_id"])
        balance_before = self.accounts.calculate_current_balance(self.account_a.account_id)

        updated = self.finance.update_transaction(
            transaction_id,
            transaction_date=date(2026, 8, 21),
            transaction_type="expense",
            category="Makan",
            amount=16_000_000,
            note="Annual payment",
            account_id=self.account_a.account_id,
            expense_type="periodic",
            coverage_months=12,
        )

        self.assertEqual(updated["transaction_id"], transaction_id)
        self.assertEqual(updated["account_id"], self.account_a.account_id)
        self.assertEqual(updated["amount"], 16_000_000)
        self.assertEqual(updated["expense_type"], "periodic")
        self.assertEqual(updated["coverage_months"], 12)
        self.assertEqual(
            self.accounts.calculate_current_balance(self.account_a.account_id),
            balance_before,
        )

    def test_delete_and_activity_lifecycle_follow_linked_transactions(self) -> None:
        transaction = self._save("expense", 600_000)
        transaction_id = str(transaction["transaction_id"])

        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), -100_000)
        self.assertFalse(self.accounts.is_initial_balance_editable(self.account_a.account_id))
        with self.assertRaisesRegex(ValueError, "tidak dapat dihapus"):
            self.accounts.delete_account(self.account_a.account_id)

        self.finance.delete_transaction(transaction_id)
        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 500_000)
        self.assertTrue(self.accounts.is_initial_balance_editable(self.account_a.account_id))

    def test_legacy_null_account_stays_editable_and_does_not_affect_balance(self) -> None:
        legacy = self.finance.prepare_transaction(
            transaction_date=date.today(), transaction_type="expense",
            category="Legacy", amount=50_000, note="legacy", account_id=None,
        )
        self.sheet_service.append(legacy)

        self.assertEqual(self.accounts.calculate_current_balance(self.account_a.account_id), 500_000)
        self.finance.update_transaction(
            str(legacy["transaction_id"]), transaction_date=date.today(),
            transaction_type="expense", category="Legacy", amount=60_000,
            note="still legacy", account_id=None,
        )
        self.assertIsNone(
            self.sheet_service.transactions[str(legacy["transaction_id"])]["account_id"]
        )


if __name__ == "__main__":
    unittest.main()
