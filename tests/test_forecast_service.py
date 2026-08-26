"""Regression tests for Forecast V2 category and Goal calculations."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

import pandas as pd

from models.account import Account
from models.goal import Goal
from services.forecast_service import ForecastService


class _FakeAnalyticsService:
    """Return deterministic transaction data without Google Sheets access."""

    def __init__(self, transactions: list[dict[str, object]]) -> None:
        self._transactions = pd.DataFrame(transactions)
        self.sheet_service = None
        self.calls = 0

    def get_transactions(self, **_: object) -> pd.DataFrame:
        """Return all test records so ForecastService owns source filtering."""

        self.calls += 1
        return self._transactions.copy()


class _FakeAccountService:
    """Return deterministic active Account balances for Financial Outlook tests."""

    def __init__(self, balance: int = 0) -> None:
        self.account = Account(
            account_id="account-1",
            account_name="Makan",
            account_location="DANA",
            initial_balance=balance,
            tracking_start_date="2026-01-01",
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        self.balance = balance

    def get_account_summaries(self) -> list[dict[str, object]]:
        """Return one active Account summary."""

        return [{"account": self.account, "current_balance": self.balance}]

    def get_current_balance_summary(self) -> dict[str, int]:
        """Match the shared AccountService system-balance contract."""

        return {"current_balance": self.balance, "active_account_count": 1}


class _FakeGoalService:
    """Return Goal V2 summaries precomputed by the test scenario."""

    def __init__(self, summaries: list[dict[str, object]]) -> None:
        self._summaries = summaries

    def get_goal_summaries(self, _: date) -> list[dict[str, object]]:
        """Return configured, Account-derived Goal summaries."""

        return self._summaries


class ForecastServiceTests(unittest.TestCase):
    """Verify Forecast V2 never uses legacy income or manual Goal balances."""

    TODAY = date(2026, 8, 20)

    def _service(
        self,
        transactions: list[dict[str, object]],
        *,
        balance: int = 0,
        goal_summaries: list[dict[str, object]] | None = None,
    ) -> ForecastService:
        """Create ForecastService with deterministic service dependencies."""

        return ForecastService(
            analytics_service=_FakeAnalyticsService(transactions),
            account_service=_FakeAccountService(balance),
            goal_service=_FakeGoalService(goal_summaries or []),
        )

    @staticmethod
    def _category_records(
        category: str,
        start: date,
        offsets: list[int],
        amount: int = 100,
    ) -> list[dict[str, object]]:
        """Build Expense records with controllable coverage and active days."""

        return [
            {
                "date": start + timedelta(days=offset),
                "type": "expense",
                "category": category,
                "amount": amount,
            }
            for offset in offsets
        ]

    def _forecast_for(
        self,
        records: list[dict[str, object]],
        category: str = "Makan",
    ) -> dict[str, object]:
        """Return one category forecast from the standard test date."""

        result = self._service(records).get_expense_forecast(self.TODAY)
        return next(item for item in result["categories"] if item["category"] == category)

    def test_sparse_categories_are_not_eligible(self) -> None:
        """Reject coverage, transaction-count, and active-day failures separately."""

        coverage = self._forecast_for(
            self._category_records("Makan", date(2026, 8, 1), list(range(10)))
        )
        transaction_count = self._forecast_for(
            self._category_records("Makan", date(2026, 8, 1), [0, 2, 4, 6, 8, 10, 13])
        )
        active_days = self._forecast_for(
            self._category_records("Makan", date(2026, 8, 1), [0, 0, 1, 1, 3, 3, 5, 5, 8, 13])
        )

        self.assertFalse(coverage["eligible"])
        self.assertIn("Coverage kurang", coverage["ineligibility_reasons"][0])
        self.assertFalse(transaction_count["eligible"])
        self.assertIn("10 transaksi", transaction_count["ineligibility_reasons"][0])
        self.assertFalse(active_days["eligible"])
        self.assertIn("7 hari aktif", active_days["ineligibility_reasons"][0])

    def test_limited_data_category_can_produce_a_basic_forecast(self) -> None:
        """Keep strong Forecast confidence separate from basic estimate safety."""

        records = self._category_records(
            "Transport",
            date(2026, 8, 1),
            [0, 2, 4],
            amount=100,
        )
        forecast = self._forecast_for(records, "Transport")
        outlook = self._service(records).get_financial_outlook(
            ["Transport"],
            self.TODAY,
        )

        self.assertFalse(forecast["eligible"])
        self.assertEqual(forecast["forecast_data_quality"], "limited")
        self.assertTrue(forecast["can_forecast"])
        self.assertIsInstance(forecast["estimated_month_total"], int)
        self.assertEqual(outlook["selected_categories"][0]["category"], "Transport")

    def test_truly_insufficient_category_does_not_fabricate_forecast(self) -> None:
        """A category below basic data thresholds remains an explicit empty state."""

        records = self._category_records(
            "Hiburan",
            date(2026, 8, 1),
            [0, 1],
            amount=100,
        )
        forecast = self._forecast_for(records, "Hiburan")

        self.assertEqual(forecast["forecast_data_quality"], "insufficient")
        self.assertFalse(forecast["can_forecast"])
        self.assertIsNone(forecast["estimated_month_total"])

    def test_optimization_uses_prior_history_for_a_comparable_period(self) -> None:
        """Current-month spending is compared with prior history through today."""

        history = self._category_records(
            "Transport",
            date(2026, 7, 1),
            list(range(7)),
            amount=100,
        )
        current = self._category_records(
            "Transport",
            date(2026, 8, 10),
            [0],
            amount=2_500,
        )
        forecast = self._forecast_for(history + current, "Transport")

        self.assertTrue(forecast["optimization_history_sufficient"])
        self.assertEqual(forecast["optimization_comparison_days"], 20)
        self.assertEqual(forecast["optimization_historical_normal"], 2_000)
        self.assertEqual(forecast["optimization_current_spending"], 2_500)
        self.assertEqual(forecast["optimization_excess"], 500)

    def test_eligible_category_uses_all_available_14_day_history(self) -> None:
        """Use all history when coverage is 14 to 29 calendar days."""

        records = self._category_records("Makan", date(2026, 8, 1), list(range(10)) + [13])
        forecast = self._forecast_for(records)

        self.assertTrue(forecast["eligible"])
        self.assertEqual(forecast["historical_coverage_days"], 14)
        self.assertEqual(forecast["historical_window_days"], 14)
        self.assertEqual(forecast["average_daily_spending"], 1100 / 14)

    def test_locked_rolling_windows_are_selected(self) -> None:
        """Select 30, 60, and 90-day windows at the locked thresholds."""

        self.assertEqual(ForecastService._select_window_days(29), 29)
        self.assertEqual(ForecastService._select_window_days(30), 30)
        self.assertEqual(ForecastService._select_window_days(59), 30)
        self.assertEqual(ForecastService._select_window_days(60), 60)
        self.assertEqual(ForecastService._select_window_days(89), 60)
        self.assertEqual(ForecastService._select_window_days(90), 90)

    def test_average_uses_calendar_days_and_month_projection(self) -> None:
        """Keep zero-spending calendar days in the denominator and horizon."""

        records = self._category_records(
            "Makan",
            date(2026, 8, 1),
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 13],
            amount=140,
        )
        forecast = self._forecast_for(records)

        self.assertEqual(forecast["average_daily_spending"], 100)
        self.assertEqual(forecast["spent_so_far_this_month"], 1400)
        self.assertEqual(forecast["projected_remaining_expense"], 1100)
        self.assertEqual(forecast["estimated_month_total"], 2500)

    def test_selected_aggregation_uses_only_future_expense(self) -> None:
        """Subtract projected future selected expense once from active balance."""

        makan = self._category_records("Makan", date(2026, 8, 1), list(range(10)) + [13])
        transport = self._category_records("Transport", date(2026, 8, 1), list(range(10)) + [13], 200)
        service = self._service(makan + transport, balance=10_000)
        outlook = service.get_financial_outlook(["Makan", "Transport"], self.TODAY)

        expected = sum(
            item["projected_remaining_expense"]
            for item in outlook["selected_categories"]
        )
        self.assertEqual(outlook["projected_selected_expense"], expected)
        self.assertEqual(
            outlook["estimated_balance_after_selected_spending"],
            10_000 - expected,
        )

    def test_global_outlook_ignores_empty_detail_selection(self) -> None:
        """Financial Outlook includes usable forecasts even without detail cards."""

        records = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
        )
        outlook = self._service(records, balance=10_000).get_financial_outlook(
            [],
            self.TODAY,
        )

        self.assertEqual(outlook["current_balance"], 10_000)
        self.assertGreater(outlook["global_projected_remaining_spending"], 0)
        self.assertEqual(
            outlook["global_estimated_balance"],
            10_000 - outlook["global_projected_remaining_spending"],
        )
        trajectory = outlook["balance_trajectory"]
        self.assertEqual(trajectory[0]["date"], self.TODAY)
        self.assertEqual(trajectory[0]["estimated_balance"], 10_000)
        self.assertEqual(
            trajectory[-1]["estimated_balance"],
            outlook["global_estimated_balance"],
        )

    def test_detail_selection_does_not_change_global_outlook_or_trajectory(self) -> None:
        """Detail inspection selection cannot alter Financial Outlook facts."""

        makan = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
            amount=100,
        )
        transport = self._category_records(
            "Transport",
            date(2026, 8, 1),
            list(range(10)) + [13],
            amount=200,
        )
        service = self._service(makan + transport, balance=1_000)
        makan_only = service.get_financial_outlook(["Makan"], self.TODAY)
        combined = service.get_financial_outlook(
            ["Makan", "Transport"],
            self.TODAY,
        )

        self.assertEqual(
            makan_only["global_projected_remaining_spending"],
            combined["global_projected_remaining_spending"],
        )
        self.assertEqual(
            makan_only["global_estimated_balance"],
            combined["global_estimated_balance"],
        )
        trajectory = makan_only["balance_trajectory"]
        self.assertEqual(trajectory[0]["estimated_balance"], 1_000)
        self.assertEqual(
            trajectory[-1]["estimated_balance"],
            makan_only["global_estimated_balance"],
        )
        self.assertEqual(
            trajectory[-1]["cumulative_selected_spending"],
            makan_only["global_projected_remaining_spending"],
        )

    def test_selected_limited_forecast_contributes_and_negative_balance_is_retained(self) -> None:
        """Limited selected forecasts affect Outlook without clamping balance."""

        records = self._category_records(
            "Transport",
            date(2026, 8, 1),
            [0, 2, 4],
            amount=100,
        )
        outlook = self._service(records, balance=50).get_financial_outlook(
            ["Transport"],
            self.TODAY,
        )

        self.assertEqual(
            outlook["selected_categories"][0]["forecast_data_quality"],
            "limited",
        )
        self.assertLess(outlook["estimated_balance_after_selected_spending"], 0)
        spending = [
            point["projected_spending_today"]
            for point in outlook["balance_trajectory"][1:]
        ]
        self.assertEqual(sum(spending), outlook["projected_selected_expense"])

    def test_limited_forecast_is_included_in_global_outlook(self) -> None:
        """A usable Limited category enters global projection without selection."""

        makan = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
            amount=100,
        )
        transport = self._category_records(
            "Transport",
            date(2026, 8, 1),
            [0, 2, 4],
            amount=100,
        )
        service = self._service(makan + transport, balance=10_000)
        outlook = service.get_financial_outlook(["Makan"], self.TODAY)

        self.assertEqual(
            [item["category"] for item in outlook["global_forecast_categories"]],
            ["Makan", "Transport"],
        )

    def test_global_outlook_excludes_insufficient_categories(self) -> None:
        """Only sufficient and usable limited forecasts enter global spending."""

        sufficient = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
            amount=100,
        )
        limited = self._category_records(
            "Transport",
            date(2026, 8, 2),
            [0, 2, 4],
            amount=200,
        )
        insufficient = self._category_records(
            "Hiburan",
            date(2026, 8, 2),
            [0, 1],
            amount=500,
        )
        outlook = self._service(
            sufficient + limited + insufficient,
            balance=10_000,
        ).get_financial_outlook([], self.TODAY)

        names = [item["category"] for item in outlook["global_forecast_categories"]]
        self.assertEqual(names, ["Makan", "Transport"])
        self.assertEqual(
            outlook["global_projected_remaining_spending"],
            sum(int(item["projected_remaining_expense"]) for item in outlook["global_forecast_categories"]),
        )

    def test_periodic_and_one_off_expenses_do_not_train_daily_behavior(self) -> None:
        """Classified cash facts remain auditable without inflating forecasts."""

        normal = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
            amount=100,
        )
        classified = normal + [
            {
                "date": date(2026, 8, 15),
                "type": "expense",
                "category": "Makan",
                "amount": 16_000_000,
                "expense_type": "periodic",
                "coverage_months": 12,
            },
            {
                "date": date(2026, 8, 16),
                "type": "expense",
                "category": "Makan",
                "amount": 4_000_000,
                "expense_type": "one-off",
            },
        ]

        result = self._service(classified, balance=50_000_000).get_expense_forecast(
            self.TODAY
        )
        forecast = result["categories"][0]
        breakdown = result["classification_breakdown"]

        self.assertEqual(forecast["raw_transaction_count"], 13)
        self.assertEqual(forecast["training_transaction_count"], 11)
        self.assertEqual(forecast["training_spending"], 1_100)
        self.assertEqual(forecast["average_daily_spending"], 1_100 / 14)
        self.assertEqual(breakdown["periodic_raw_expense"], 16_000_000)
        self.assertEqual(breakdown["periodic_monthly_equivalent"], 1_333_333)
        self.assertEqual(breakdown["one_off_excluded_amount"], 4_000_000)
        self.assertEqual(
            breakdown["normalized_spending_so_far"],
            1_100 + 1_333_333,
        )

    def test_current_period_history_can_create_limited_optimization_baseline(self) -> None:
        """Strong current-period activity is a marked fallback without prior data."""

        records = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(14)),
            amount=100,
        )
        forecast = self._forecast_for(records)

        self.assertTrue(forecast["optimization_history_sufficient"])
        self.assertEqual(
            forecast["optimization_baseline_type"],
            "limited_current_period",
        )
        self.assertEqual(forecast["optimization_current_spending"], 700)
        self.assertEqual(forecast["optimization_historical_normal"], 700)

    def test_non_expense_records_do_not_enter_category_forecast(self) -> None:
        """Exclude Income, Transfer, and Adjustment records from Expense Forecast."""

        expense = self._category_records("Makan", date(2026, 8, 1), list(range(10)) + [13])
        records = expense + [
            {"date": date(2026, 8, 14), "type": "income", "category": "Makan", "amount": 9000},
            {"date": date(2026, 8, 15), "type": "transfer", "category": "Makan", "amount": 9000},
            {"date": date(2026, 8, 16), "type": "adjustment", "category": "Makan", "amount": 9000},
        ]
        forecast = self._forecast_for(records)

        self.assertEqual(forecast["transaction_count"], len(expense))
        self.assertEqual(forecast["spent_so_far_this_month"], len(expense) * 100)

    def test_goal_completion_requires_positive_sufficient_pace(self) -> None:
        """Produce completion only for a Goal with usable positive pace."""

        goal = self._goal()
        sufficient = self._goal_summary(goal, pace=200, sufficient=True)
        zero_pace = self._goal_summary(goal, pace=0, sufficient=True)
        insufficient = self._goal_summary(goal, pace=None, sufficient=False)

        ready = self._service([], goal_summaries=[sufficient]).get_goal_forecast(self.TODAY)["goals"][0]
        unavailable = self._service([], goal_summaries=[zero_pace]).get_goal_forecast(self.TODAY)["goals"][0]
        sparse = self._service([], goal_summaries=[insufficient]).get_goal_forecast(self.TODAY)["goals"][0]

        self.assertEqual(ready["projected_completion"], date(2026, 12, 20))
        self.assertIn("non-positive", unavailable["projected_completion_label"])
        self.assertEqual(sparse["projected_completion_label"], "Insufficient Allocation History")

    def test_goal_health_and_deadline_conditions_are_preserved(self) -> None:
        """Keep achieved, overdue, and no-deadline V2 states transparent."""

        achieved = self._goal_summary(self._goal(), current=1000, remaining=0, health="Achieved")
        overdue = self._goal_summary(self._goal(), health="Overdue")
        no_deadline_goal = self._goal(deadline=None)
        no_deadline = self._goal_summary(no_deadline_goal, health="No Deadline", pace=100)
        result = self._service([], goal_summaries=[achieved, overdue, no_deadline]).get_goal_forecast(self.TODAY)["goals"]

        self.assertEqual(result[0]["projected_completion_label"], "Already achieved")
        self.assertEqual(result[1]["health"], "Overdue")
        self.assertEqual(result[2]["health"], "No Deadline / Pace Available")

    def test_actual_expense_so_far_uses_only_current_month_expenses(self) -> None:
        """Income, movements, and prior-month rows never enter the fact total."""

        records = [
            {"date": date(2026, 8, 2), "type": "expense", "category": "Makan", "amount": 100},
            {"date": date(2026, 8, 3), "type": "expense", "category": "", "amount": 200},
            {"date": date(2026, 8, 4), "type": "income", "category": "Gaji", "amount": 900},
            {"date": date(2026, 8, 5), "type": "transfer", "category": "Makan", "amount": 800},
            {"date": date(2026, 8, 6), "type": "adjustment", "category": "Makan", "amount": 700},
            {"date": date(2026, 7, 31), "type": "expense", "category": "Makan", "amount": 600},
        ]

        result = self._service(records).get_expense_forecast(self.TODAY)

        self.assertEqual(result["actual_expense_so_far"], 300)

    def test_spending_limit_status_uses_actual_plus_selected_future_only(self) -> None:
        """Tracked spending never double-counts actual selected-category expense."""

        status = ForecastService.get_monthly_spending_limit_status(
            monthly_spending_limit=3_000,
            expense_forecast={"actual_expense_so_far": 2_000},
            financial_outlook={"projected_selected_expense": 500},
        )

        self.assertEqual(status["projected_tracked_spending"], 2_500)
        self.assertFalse(status["spending_risk"])
        self.assertEqual(status["spending_limit_usage_percent"], 2500 / 3000 * 100)

    def test_spending_limit_status_is_local_and_does_not_fetch_transactions(self) -> None:
        """Derived limit status accepts loaded Forecast data without a repository read."""

        status = ForecastService.get_monthly_spending_limit_status(
            monthly_spending_limit=1_000,
            expense_forecast={"actual_expense_so_far": 900},
            financial_outlook={"projected_selected_expense": 300},
        )

        self.assertTrue(status["spending_risk"])
        self.assertEqual(status["spending_limit_gap"], 200)

    def test_global_outlook_uses_one_loaded_transaction_snapshot(self) -> None:
        """Detail, risk, and global Outlook reuse the Expense Forecast snapshot."""

        records = self._category_records(
            "Makan",
            date(2026, 8, 1),
            list(range(10)) + [13],
        )
        analytics = _FakeAnalyticsService(records)
        service = ForecastService(
            analytics_service=analytics,
            account_service=_FakeAccountService(10_000),
            goal_service=_FakeGoalService([]),
        )

        expense_forecast = service.get_expense_forecast(self.TODAY)
        outlook = service.get_financial_outlook(
            ["Makan"],
            expense_forecast=expense_forecast,
        )
        status = service.get_monthly_spending_limit_status(
            monthly_spending_limit=2_000,
            expense_forecast=expense_forecast,
            financial_outlook=outlook,
        )

        self.assertEqual(analytics.calls, 1)
        self.assertEqual(
            status["projected_normalized_monthly_spending"],
            status["normalized_monthly_spending_so_far"]
            + outlook["global_projected_remaining_spending"],
        )

    @staticmethod
    def _goal(deadline: str | None = "2026-12-31") -> Goal:
        """Build an immutable Goal V2 fixture."""

        return Goal(
            goal_id="goal-1",
            account_id="account-1",
            target_amount=1000,
            deadline=deadline,
            priority="high",
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )

    @staticmethod
    def _goal_summary(
        goal: Goal,
        *,
        current: int = 200,
        remaining: int = 800,
        health: str = "On Track",
        pace: int | None = 200,
        sufficient: bool = True,
    ) -> dict[str, object]:
        """Build one GoalService-compatible summary fixture."""

        account = Account(
            account_id="account-1",
            account_name="Laptop",
            account_location="BCA",
            initial_balance=0,
            tracking_start_date="2026-01-01",
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        return {
            "goal": goal,
            "account": account,
            "current_progress": current,
            "remaining_amount": remaining,
            "progress_percent": current / goal.target_amount * 100,
            "required_monthly_contribution": 200 if goal.deadline else None,
            "contribution_pace": {"is_sufficient": sufficient, "monthly_amount": pace, "months": 2},
            "health": health,
        }


if __name__ == "__main__":
    unittest.main()
