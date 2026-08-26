"""Regression tests for Settings ownership and scoped data management."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from models.user_settings import UserSettings
from services.account_service import AccountService
from services.data_management_service import DataManagementService
from services.finance_service import FinanceService
from services.forecast_service import ForecastService
from services.settings_service import SettingsService


class _FakeSheetService:
    """In-memory transaction repository for non-destructive backup tests."""

    def __init__(self, transaction: dict[str, object]) -> None:
        self.dataframe = pd.DataFrame([transaction])
        self.replaced_transactions: list[dict[str, object]] | None = None

    def get_transactions_dataframe(self) -> pd.DataFrame:
        """Return a normalized copy of persisted Transaction data."""

        return self.dataframe.copy()

    @staticmethod
    def get_accounts() -> list[dict[str, object]]:
        """Provide the linked Account needed by transaction restore validation."""

        return [
            {
                "account_id": "account-123",
                "account_name": "Backup account",
                "account_location": "DANA",
                "initial_balance": 0,
                "tracking_start_date": "2026-08-01",
                "status": "active",
                "created_at": "2026-08-01T00:00:00",
                "updated_at": "2026-08-01T00:00:00",
            }
        ]

    def replace_transactions(self, transactions: list[dict[str, object]]) -> None:
        """Capture a validated replacement without writing external data."""

        self.replaced_transactions = transactions


class SettingsCleanupTests(unittest.TestCase):
    """Verify legacy configuration cannot become a V2 financial source."""

    def test_legacy_values_are_preserved_but_settings_has_no_financial_api(self) -> None:
        """Keep local compatibility while retiring V1 balance, goal, and income APIs."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "settings.json"
            legacy_payload = {
                "name": "Haida",
                "current_balance": 99_999_999,
                "monthly_income": 88_888_888,
                "monthly_saving_target": 77_777_777,
                "payday": 15,
                "risk_preference": "Aggressive",
            }
            path.write_text(json.dumps(legacy_payload), encoding="utf-8")
            service = SettingsService(path)

            loaded = service.load()
            service.save(UserSettings(**{**loaded.to_dict(), "name": "Updated"}))
            persisted = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(persisted["current_balance"], 99_999_999)
        self.assertEqual(persisted["monthly_income"], 88_888_888)
        self.assertEqual(persisted["monthly_saving_target"], 77_777_777)
        self.assertFalse(hasattr(service, "get_financial_profile"))
        self.assertFalse(hasattr(service, "get_financial_goals"))
        self.assertFalse(hasattr(service, "create_financial_goal"))

    def test_legacy_balance_and_income_cannot_change_v2_services(self) -> None:
        """Use Account and Transaction services, never manual Settings values."""

        class AccountSheet:
            """Minimal Account repository with no external dependencies."""

            def __init__(self) -> None:
                self.accounts: dict[str, dict[str, object]] = {}

            def append_account(self, account: dict[str, object]) -> None:
                self.accounts[str(account["account_id"])] = dict(account)

            def get_accounts(self) -> list[dict[str, object]]:
                return list(self.accounts.values())

            def get_transactions(self) -> list[dict[str, object]]:
                return []

        class Analytics:
            """Return one actual Income transaction for Forecast V2."""

            sheet_service = None

            @staticmethod
            def get_transactions(**_: object) -> pd.DataFrame:
                return pd.DataFrame(
                    [
                        {
                            "date": "2026-08-10",
                            "type": "income",
                            "amount": 125_000,
                        }
                    ]
                )

        class Accounts:
            """Provide the AccountService balance contract required by Forecast."""

            @staticmethod
            def get_current_balance_summary() -> dict[str, int]:
                return {"current_balance": 500_000, "active_account_count": 1}

        class Goals:
            """Avoid persistence because this test reads only actual Income."""

            @staticmethod
            def get_goal_summaries(_: date) -> list[dict[str, object]]:
                return []

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "settings.json"
            path.write_text(
                json.dumps({"current_balance": 99_999_999, "monthly_income": 88_888_888}),
                encoding="utf-8",
            )
            SettingsService(path).load()

            account_service = AccountService(AccountSheet())
            account = account_service.create_account(
                account_name="Cash",
                account_location="DANA",
                initial_balance=500_000,
            )
            forecast = ForecastService(
                analytics_service=Analytics(),
                account_service=Accounts(),
                goal_service=Goals(),
            )

        self.assertEqual(account_service.calculate_current_balance(account.account_id), 500_000)
        self.assertEqual(forecast.get_actual_monthly_income(date(2026, 8, 20)), 125_000)

    def test_forecast_preferences_persist_locally_without_domain_storage(self) -> None:
        """Saving Candidates and spending limit remain lightweight local preferences."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_path = Path(temporary_directory) / "settings.json"
            service = SettingsService(storage_path)
            service.save_saving_candidates({"Makan": True})
            service.save_monthly_spending_limit(3_000_000)

            self.assertEqual(
                service.get_saving_candidates(["Makan", "Transport"]),
                {"Makan": True, "Transport": False},
            )
            self.assertEqual(service.get_monthly_spending_limit(), 3_000_000)
            self.assertEqual(
                SettingsService(storage_path).get_monthly_spending_limit(),
                3_000_000,
            )

    def test_zero_or_invalid_spending_limit_is_safely_disabled(self) -> None:
        """Local preference validation must never create a negative limit."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            service = SettingsService(Path(temporary_directory) / "settings.json")
            service.save_monthly_spending_limit(0)
            self.assertEqual(service.get_monthly_spending_limit(), 0)
            with self.assertRaises(ValueError):
                service.save_monthly_spending_limit(-1)


class TransactionBackupTests(unittest.TestCase):
    """Verify explicitly scoped backups retain V2 Transaction identity fields."""

    def setUp(self) -> None:
        """Create a stable V2 transaction record for each test."""

        self.transaction = FinanceService.build_transaction(
            {
                "transaction_type": "expense",
                "category": "Makan",
                "amount": 50_000,
                "note": "Bakso",
                "account_id": "account-123",
                "expense_type": "periodic",
                "coverage_months": 12,
            },
            transaction_date=date(2026, 8, 24),
        )
        self.fake_sheet = _FakeSheetService(self.transaction)

    def test_transaction_only_backup_preserves_v2_identity_and_declares_scope(self) -> None:
        """Make the limited backup scope explicit without losing transaction IDs."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            service = DataManagementService(
                self.fake_sheet,
                Path(temporary_directory),
            )
            backup = service.create_backup()

        self.assertEqual(backup["scope"], "transactions_only")
        self.assertEqual(
            backup["excluded_datasets"],
            ["accounts", "account_movements", "goals"],
        )
        self.assertEqual(
            backup["transactions"][0]["transaction_id"],
            self.transaction["transaction_id"],
        )
        self.assertEqual(
            backup["transactions"][0]["account_id"],
            self.transaction["account_id"],
        )
        self.assertEqual(backup["transactions"][0]["expense_type"], "periodic")
        self.assertEqual(backup["transactions"][0]["coverage_months"], 12)

    def test_restore_preserves_periodic_expense_metadata(self) -> None:
        """Restore classification metadata without mutating the financial amount."""

        transaction = FinanceService.build_transaction(
            {
                "transaction_type": "expense",
                "category": "Tagihan & Langganan",
                "amount": 1_200_000,
                "note": "Langganan tahunan",
                "expense_type": "periodic",
                "coverage_months": 12,
            },
            transaction_date=date(2026, 8, 24),
        )
        fake_sheet = _FakeSheetService(transaction)

        with tempfile.TemporaryDirectory() as temporary_directory:
            service = DataManagementService(fake_sheet, Path(temporary_directory))
            backup = service.create_backup()
            restored_count = service.restore_backup(backup["backup_id"])

        self.assertEqual(restored_count, 1)
        self.assertIsNotNone(fake_sheet.replaced_transactions)
        restored = fake_sheet.replaced_transactions[0]
        self.assertEqual(restored["transaction_id"], transaction["transaction_id"])
        self.assertEqual(restored["amount"], 1_200_000)
        self.assertEqual(restored["expense_type"], "periodic")
        self.assertEqual(restored["coverage_months"], 12)

    def test_invalid_backup_is_rejected_before_replacing_transactions(self) -> None:
        """Validate transaction schema and IDs before any destructive write."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            backup_directory = Path(temporary_directory)
            backup_id = "transactions-20260824-000000-000000"
            (backup_directory / f"{backup_id}.json").write_text(
                json.dumps(
                    {
                        "created_at": "2026-08-24T00:00:00",
                        "transaction_count": 1,
                        "transactions": [{"date": "not-a-date"}],
                    }
                ),
                encoding="utf-8",
            )
            service = DataManagementService(self.fake_sheet, backup_directory)

            with self.assertRaisesRegex(ValueError, "invalid transaction data"):
                service.restore_backup(backup_id)

        self.assertIsNone(self.fake_sheet.replaced_transactions)


if __name__ == "__main__":
    unittest.main()
