"""Tests for the pure, non-persistent Scenario Simulator service."""

from __future__ import annotations

from datetime import date
import unittest

from models.account import Account
from models.goal import Goal
from services.scenario_service import ScenarioService


class ScenarioServiceTests(unittest.TestCase):
    """Verify Scenario calculations cannot alter financial source-of-truth data."""

    TODAY = date(2026, 8, 20)

    def setUp(self) -> None:
        """Create one selected Forecast and one eligible Goal fixture."""

        self.service = ScenarioService()
        self.goal = Goal(
            goal_id="goal-1",
            account_id="account-1",
            target_amount=1_000,
            deadline="2026-10-31",
            priority="high",
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        account = Account(
            account_id="account-1",
            account_name="Emergency Fund",
            account_location="DANA",
            initial_balance=400,
            tracking_start_date="2026-01-01",
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        self.outlook = {
            "as_of": self.TODAY,
            "current_balance": 1_000,
            "global_projected_remaining_spending": 500,
            "global_estimated_balance": 500,
            "projected_selected_expense": 500,
            "estimated_balance_after_selected_spending": 500,
            "selected_categories": [
                {
                    "category": "Makan",
                    "projected_remaining_expense": 400,
                    "forecast_data_quality": "sufficient",
                },
                {
                    "category": "Transport",
                    "projected_remaining_expense": 100,
                    "forecast_data_quality": "limited",
                },
            ],
            "global_forecast_categories": [
                {
                    "category": "Makan",
                    "projected_remaining_expense": 400,
                    "forecast_data_quality": "sufficient",
                },
                {
                    "category": "Transport",
                    "projected_remaining_expense": 100,
                    "forecast_data_quality": "limited",
                },
            ],
            "monthly_spending_limit_status": {
                "configured": True,
                "monthly_spending_limit": 1_000,
                "projected_normalized_monthly_spending": 1_300,
                "spending_risk": True,
                "spending_limit_gap": 300,
            },
            "balance_trajectory": [
                {"date": self.TODAY, "estimated_balance": 1_000},
                {"date": date(2026, 8, 31), "estimated_balance": 500},
            ],
        }
        self.goal_forecast = {
            "goals": [
                {
                    "goal": self.goal,
                    "account": account,
                    "current_progress": 400,
                    "remaining_amount": 600,
                    "contribution_pace": {
                        "is_sufficient": True,
                        "monthly_amount": 100,
                        "months": 2,
                    },
                    "required_monthly_contribution": 200,
                    "health": "At Risk",
                    "projected_completion_label": "20 Feb 2027",
                }
            ]
        }

    def test_nominal_reduction_reconciles_spending_and_balance(self) -> None:
        """A nominal reduction changes only future simulated values."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Makan", "mode": "amount", "value": 200}],
        )

        self.assertEqual(result["scenario_projected_remaining_spending"], 300)
        self.assertEqual(result["potential_saving"], 200)
        self.assertEqual(result["scenario_estimated_balance"], 700)
        self.assertEqual(result["current_balance"], 1_000)
        self.assertEqual(result["balance_improvement"], 200)
        self.assertEqual(result["balance_improvement_percentage"], 40.0)

    def test_percentage_reduction_and_limited_forecast_are_supported(self) -> None:
        """A limited basic Forecast can be adjusted by percentage in Scenario."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Transport", "mode": "percentage", "value": 10}],
        )

        self.assertEqual(result["potential_saving"], 10)
        self.assertEqual(result["category_impacts"][1]["scenario_future_expense"], 90)
        self.assertEqual(result["category_impacts"][1]["forecast_data_quality"], "limited")

    def test_invalid_category_reduction_is_rejected(self) -> None:
        """Scenario never silently clamps an amount beyond its baseline."""

        with self.assertRaisesRegex(ValueError, "tidak boleh melebihi"):
            self.service.simulate(
                outlook=self.outlook,
                goal_forecast=self.goal_forecast,
                adjustments=[{"category": "Makan", "mode": "amount", "value": 401}],
            )
        with self.assertRaisesRegex(ValueError, "100%"):
            self.service.simulate(
                outlook=self.outlook,
                goal_forecast=self.goal_forecast,
                adjustments=[{"category": "Makan", "mode": "percentage", "value": 101}],
            )

    def test_multiple_adjustments_aggregate_and_trajectory_reconciles(self) -> None:
        """Both balance lines start and end at their matching financial metrics."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[
                {"category": "Makan", "mode": "amount", "value": 100},
                {"category": "Transport", "mode": "percentage", "value": 50},
            ],
        )

        self.assertEqual(result["potential_saving"], 150)
        self.assertEqual(result["baseline_trajectory"][0]["estimated_balance"], 1_000)
        self.assertEqual(result["scenario_trajectory"][0]["estimated_balance"], 1_000)
        self.assertEqual(result["baseline_trajectory"][-1]["estimated_balance"], 500)
        self.assertEqual(result["scenario_trajectory"][-1]["estimated_balance"], 650)

    def test_goal_allocation_is_hypothetical_and_cannot_overallocate(self) -> None:
        """Goal allocation updates Scenario pace without mutating its source summary."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Makan", "mode": "amount", "value": 300}],
            goal_allocations={"goal-1": 250},
        )

        impact = result["goal_impacts"][0]
        self.assertEqual(result["total_goal_allocation"], 250)
        self.assertEqual(result["unallocated_saving"], 50)
        self.assertEqual(impact["scenario_monthly_pace"], 350)
        self.assertEqual(impact["simulated_current_progress"], 650)
        self.assertEqual(self.goal_forecast["goals"][0]["current_progress"], 400)
        with self.assertRaisesRegex(ValueError, "melebihi Potential Saving"):
            self.service.simulate(
                outlook=self.outlook,
                goal_forecast=self.goal_forecast,
                adjustments=[{"category": "Makan", "mode": "amount", "value": 100}],
                goal_allocations={"goal-1": 101},
            )

    def test_goal_allocation_does_not_reduce_balance_improvement(self) -> None:
        """Goal planning consumes capacity, not the improved Scenario balance."""

        without_allocation = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Makan", "mode": "amount", "value": 200}],
        )
        with_allocation = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Makan", "mode": "amount", "value": 200}],
            goal_allocations={"goal-1": 150},
        )

        self.assertEqual(without_allocation["unallocated_saving"], 200)
        self.assertEqual(with_allocation["unallocated_saving"], 50)
        self.assertEqual(
            with_allocation["balance_improvement"],
            without_allocation["balance_improvement"],
        )
        self.assertEqual(
            with_allocation["scenario_estimated_balance"],
            without_allocation["scenario_estimated_balance"],
        )

    def test_zero_baseline_has_safe_improvement_percentage(self) -> None:
        """Avoid division by zero when the Financial Outlook baseline is zero."""

        outlook = dict(self.outlook)
        outlook.update(
            {
                "current_balance": 0,
                "global_projected_remaining_spending": 0,
                "global_estimated_balance": 0,
                "projected_selected_expense": 0,
                "estimated_balance_after_selected_spending": 0,
                "selected_categories": [],
                "global_forecast_categories": [],
                "balance_trajectory": [{"date": self.TODAY, "estimated_balance": 0}],
            }
        )
        result = self.service.simulate(outlook=outlook, goal_forecast=self.goal_forecast)

        self.assertEqual(result["balance_improvement"], 0)
        self.assertIsNone(result["balance_improvement_percentage"])

    def test_zero_adjustment_returns_forecast_baseline(self) -> None:
        """Reset-equivalent inputs preserve all baseline values exactly."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
        )

        self.assertEqual(result["potential_saving"], 0)
        self.assertEqual(result["scenario_projected_remaining_spending"], 500)
        self.assertEqual(result["scenario_estimated_balance"], 500)
        self.assertEqual(result["goal_impacts"], [])

    def test_scenario_compares_global_normalized_spending_and_limit(self) -> None:
        """A reduction improves the same global Outlook shown before Scenario."""

        result = self.service.simulate(
            outlook=self.outlook,
            goal_forecast=self.goal_forecast,
            adjustments=[{"category": "Makan", "mode": "amount", "value": 200}],
        )

        self.assertEqual(result["baseline_projected_remaining_spending"], 500)
        self.assertEqual(result["scenario_projected_remaining_spending"], 300)
        self.assertEqual(result["baseline_projected_normalized_monthly_spending"], 1_300)
        self.assertEqual(result["scenario_projected_normalized_monthly_spending"], 1_100)
        self.assertTrue(result["scenario_spending_risk"])
        self.assertEqual(result["scenario_spending_limit_gap"], 100)


if __name__ == "__main__":
    unittest.main()
