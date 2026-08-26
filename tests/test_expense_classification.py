"""Regression tests for classified Expense metadata and risk normalization."""

from __future__ import annotations

from datetime import date
import unittest

import pandas as pd

from services.finance_service import FinanceService
from services.forecast_service import ForecastService
from services.transaction_schema import (
    normalize_transaction,
    normalized_monthly_expense_contribution,
)


class _FakeAnalyticsService:
    """Return one preloaded transaction snapshot without remote dependencies."""

    def __init__(self, transactions: list[dict[str, object]]) -> None:
        self.transactions = pd.DataFrame(transactions)
        self.calls = 0

    def get_transactions(self, **_: object) -> pd.DataFrame:
        self.calls += 1
        return self.transactions.copy()


class _FakeAccountService:
    """Provide a stable actual-balance value for Forecast regression tests."""

    def get_current_balance_summary(self) -> dict[str, int]:
        return {"current_balance": 1_000_000}


class _FakeGoalService:
    """Avoid unrelated Goal worksheet construction in Forecast unit tests."""


class ExpenseClassificationTests(unittest.TestCase):
    """Protect actual cash records from analytical classification changes."""

    def test_legacy_expense_defaults_to_normal_and_income_clears_metadata(self) -> None:
        legacy_expense = normalize_transaction(
            {
                "date": "2026-08-01",
                "type": "expense",
                "category": "Makan",
                "amount": 500_000,
                "note": "Legacy",
            },
            generate_missing_id=True,
        )
        income = normalize_transaction(
            {
                "date": "2026-08-01",
                "type": "income",
                "category": "Gaji",
                "amount": 5_000_000,
                "note": "Salary",
                "expense_type": "periodic",
                "coverage_months": 12,
            },
            generate_missing_id=True,
        )

        self.assertEqual(legacy_expense["expense_type"], "normal")
        self.assertIsNone(legacy_expense["coverage_months"])
        self.assertIsNone(income["expense_type"])
        self.assertIsNone(income["coverage_months"])

    def test_monthly_contribution_obeys_each_expense_classification(self) -> None:
        normal = {"type": "expense", "amount": 500_000, "expense_type": "normal"}
        periodic = {
            "type": "expense",
            "amount": 16_000_000,
            "expense_type": "periodic",
            "coverage_months": 12,
        }
        one_off = {
            "type": "expense",
            "amount": 10_000_000,
            "expense_type": "one-off",
        }

        self.assertEqual(normalized_monthly_expense_contribution(normal), 500_000)
        self.assertEqual(normalized_monthly_expense_contribution(periodic), 1_333_333)
        self.assertEqual(normalized_monthly_expense_contribution(one_off), 0)

    def test_periodic_requires_positive_whole_coverage_and_other_types_clear_it(self) -> None:
        for invalid_coverage in (None, 0, -1, 1.5, "abc"):
            with self.assertRaises(ValueError):
                normalize_transaction(
                    {
                        "date": "2026-08-01",
                        "type": "expense",
                        "category": "Tempat Tinggal",
                        "amount": 1_000_000,
                        "note": "Rent",
                        "expense_type": "periodic",
                        "coverage_months": invalid_coverage,
                    },
                    generate_missing_id=True,
                )

        for expense_type in ("normal", "one-off"):
            transaction = normalize_transaction(
                {
                    "date": "2026-08-01",
                    "type": "expense",
                    "category": "Lainnya",
                    "amount": 1_000_000,
                    "note": "Test",
                    "expense_type": expense_type,
                    "coverage_months": 12,
                },
                generate_missing_id=True,
            )
            self.assertIsNone(transaction["coverage_months"])

    def test_classification_changes_do_not_change_identity_or_cash_values(self) -> None:
        original = normalize_transaction(
            {
                "date": "2026-08-01",
                "type": "expense",
                "category": "Lainnya",
                "amount": 10_000_000,
                "note": "Laptop",
                "account_id": "account-1",
                "expense_type": "normal",
            },
            generate_missing_id=True,
        )
        reclassified = normalize_transaction(
            {**original, "expense_type": "one-off", "coverage_months": 24},
            generate_missing_id=False,
        )

        self.assertEqual(reclassified["transaction_id"], original["transaction_id"])
        self.assertEqual(reclassified["account_id"], original["account_id"])
        self.assertEqual(reclassified["date"], original["date"])
        self.assertEqual(reclassified["amount"], original["amount"])
        self.assertIsNone(reclassified["coverage_months"])

    def test_monthly_limit_uses_normalized_not_raw_expense(self) -> None:
        reference_date = date(2026, 8, 20)
        analytics = _FakeAnalyticsService(
            [
                {
                    "date": "2026-08-02",
                    "type": "expense",
                    "category": "Makan",
                    "amount": 1_000_000,
                    "expense_type": "normal",
                    "coverage_months": None,
                },
                {
                    "date": "2026-08-03",
                    "type": "expense",
                    "category": "Transport",
                    "amount": 500_000,
                    "expense_type": "normal",
                    "coverage_months": None,
                },
                {
                    "date": "2026-08-04",
                    "type": "expense",
                    "category": "Tempat Tinggal",
                    "amount": 16_000_000,
                    "expense_type": "periodic",
                    "coverage_months": 12,
                },
            ]
        )
        service = ForecastService(
            analytics_service=analytics,
            account_service=_FakeAccountService(),
            goal_service=_FakeGoalService(),
        )
        forecast = service.get_expense_forecast(reference_date)
        outlook = service.get_financial_outlook(
            [],
            reference_date,
            expense_forecast=forecast,
        )
        status = service.get_monthly_spending_limit_status(
            monthly_spending_limit=4_000_000,
            expense_forecast=forecast,
            financial_outlook=outlook,
        )

        self.assertEqual(forecast["actual_expense_so_far"], 17_500_000)
        self.assertEqual(forecast["normalized_monthly_spending_so_far"], 2_833_333)
        self.assertFalse(status["spending_risk"])
        self.assertEqual(outlook["current_balance"], 1_000_000)
        self.assertEqual(analytics.calls, 1)

    def test_telegram_style_expense_defaults_to_normal(self) -> None:
        transaction = FinanceService.build_transaction(
            {
                "transaction_type": "expense",
                "category": "Makan",
                "amount": 25_000,
                "note": "Lunch",
                "account_id": "account-1",
            },
            transaction_date=date(2026, 8, 20),
        )

        self.assertEqual(transaction["expense_type"], "normal")
        self.assertIsNone(transaction["coverage_months"])


if __name__ == "__main__":
    unittest.main()
