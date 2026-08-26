"""Regression tests for Overview and Analytics transaction isolation."""

from __future__ import annotations

from datetime import date
import unittest

import pandas as pd

from dashboard.components.filters._helpers import category_options_for_type
from services.analytics_service import AnalyticsService
from services.category_definitions import EXPENSE_CATEGORIES, INCOME_CATEGORIES


class _FakeSheetService:
    """Return a fixed transaction dataframe without Google Sheets access."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._data = pd.DataFrame(rows)

    def get_transactions_dataframe(self) -> pd.DataFrame:
        """Return an independent dataframe for every service load."""

        return self._data.copy()


class AnalyticsServiceTests(unittest.TestCase):
    """Ensure historical analytics only counts economic Transactions."""

    def setUp(self) -> None:
        """Prepare income, expense, legacy, and non-economic record fixtures."""

        self.analytics = AnalyticsService(_FakeSheetService([
            {
                "date": "2026-08-01", "type": "income", "category": "Gaji",
                "amount": "1000", "note": "salary", "account_id": "account-1",
            },
            {
                "date": "2026-08-02", "type": "expense", "category": "Makan",
                "amount": "200", "note": "food", "account_id": None,
            },
            {
                "date": "2026-08-03", "type": "expense", "category": "Legacy Custom",
                "amount": "100", "note": "legacy", "account_id": None,
            },
            {
                "date": "2026-08-04", "type": "transfer", "category": "Transfer",
                "amount": "900", "note": "must exclude", "account_id": "account-1",
            },
            {
                "date": "2026-08-05", "type": "adjustment", "category": "Adjustment",
                "amount": "800", "note": "must exclude", "account_id": "account-1",
            },
            {
                "date": "2026-07-31", "type": "expense", "category": "Makan",
                "amount": "50", "note": "previous", "account_id": None,
            },
        ]))

    def test_dashboard_summary_uses_only_period_income_and_expense(self) -> None:
        """Transfers, adjustments, and initial balances never enter period KPIs."""

        summary = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )

        self.assertEqual(summary["income"], 1_000)
        self.assertEqual(summary["expense"], 300)
        self.assertEqual(summary["net_cashflow"], 700)
        self.assertEqual(summary["transaction_count"], 3)

    def test_historical_null_account_transactions_remain_analytically_valid(self) -> None:
        """Null Account ID does not exclude an economic historical record."""

        summary = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )

        self.assertEqual(summary["expense"], 300)
        self.assertEqual(summary["transaction_count"], 3)

    def test_expense_categories_and_recent_transactions_exclude_movements(self) -> None:
        """Movement-like rows cannot contaminate category charts or recents."""

        categories = self.analytics.get_expense_by_category(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )
        recent = self.analytics.get_recent_transactions(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
        )

        self.assertEqual(categories["amount"].sum(), 300)
        self.assertNotIn("Transfer", categories["category"].tolist())
        self.assertNotIn("Adjustment", categories["category"].tolist())
        self.assertTrue(recent["type"].isin({"income", "expense"}).all())

    def test_standard_and_legacy_categories_remain_available(self) -> None:
        """Filters expose V1 vocabulary without losing legacy stored values."""

        categories = self.analytics.get_categories()

        self.assertIn("Makan", categories)
        self.assertIn("Tagihan & Langganan", categories)
        self.assertIn("Gaji", categories)
        self.assertIn("Legacy Custom", categories)

    def test_multi_category_filter_combines_selected_categories(self) -> None:
        """Overview-style multi-category filters aggregate only selected rows."""

        summary = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category=["Makan", "Legacy Custom"],
        )
        recent = self.analytics.get_recent_transactions(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category=["Makan", "Legacy Custom"],
        )

        self.assertEqual(summary["income"], 0)
        self.assertEqual(summary["expense"], 300)
        self.assertEqual(summary["transaction_count"], 2)
        self.assertEqual(set(recent["category"]), {"Makan", "Legacy Custom"})

    def test_empty_multi_category_filter_means_all_categories(self) -> None:
        """An empty Overview selection preserves the unfiltered result set."""

        all_categories = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category="All",
        )
        empty_selection = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category=[],
        )

        self.assertEqual(empty_selection, all_categories)

    def test_single_category_filter_remains_supported_for_analytics(self) -> None:
        """Analytics drilldown retains its established single-category contract."""

        summary = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category="Makan",
        )

        self.assertEqual(summary["expense"], 200)
        self.assertEqual(summary["transaction_count"], 1)

    def test_type_and_category_filters_are_applied_together(self) -> None:
        """Type filtering remains consistent with its visible category options."""

        income = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category="Gaji",
            transaction_type="Income",
        )
        expense = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category="Makan",
            transaction_type="Expense",
        )
        mismatch = self.analytics.get_dashboard_summary(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            category="Gaji",
            transaction_type="Expense",
        )

        self.assertEqual(income["income"], 1_000)
        self.assertEqual(expense["expense"], 200)
        self.assertEqual(mismatch["transaction_count"], 0)

    def test_category_options_follow_transaction_type(self) -> None:
        """Category controls expose only the V1 vocabulary for a selected type."""

        all_categories = self.analytics.get_categories()

        self.assertEqual(
            category_options_for_type(all_categories, "Income"),
            list(INCOME_CATEGORIES),
        )
        self.assertEqual(
            category_options_for_type(all_categories, "Expense"),
            list(EXPENSE_CATEGORIES),
        )
        self.assertIn(
            "Gaji",
            category_options_for_type(all_categories, "All"),
        )
        self.assertIn(
            "Makan",
            category_options_for_type(all_categories, "All"),
        )

    def test_period_comparison_ignores_non_economic_rows(self) -> None:
        """Period comparison remains Transaction-driven after movement support."""

        comparison = self.analytics.get_period_comparison(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )

        financial = comparison["financial_comparison"]
        self.assertEqual(financial["income"]["current"], 1_000)
        self.assertEqual(financial["expense"]["current"], 300)
        self.assertEqual(financial["saving"]["current"], 700)
        self.assertEqual(financial["expense"]["previous"], 50)


if __name__ == "__main__":
    unittest.main()
