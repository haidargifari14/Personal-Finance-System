"""Regression tests for decoupled, deterministic Recommendation V1."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from models.goal import Goal
from services.recommendation_service import RecommendationService
from services.settings_service import SettingsService
from tests.test_settings_service import FakeSettingsWorksheet


class RecommendationServiceTests(unittest.TestCase):
    """Verify Saving Candidate analysis is independent of Forecast UI state."""

    TODAY = date(2026, 8, 20)

    def setUp(self) -> None:
        self.service = RecommendationService()

    @staticmethod
    def _category(
        name: str,
        *,
        estimate: int,
        current: int,
        normal: int | None,
        quality: str = "sufficient",
        optimization_sufficient: bool = True,
        baseline_type: str = "historical",
    ) -> dict[str, object]:
        """Build a Forecast V2 category fixture with optimization metadata."""

        excess = current - normal if normal is not None else None
        return {
            "category": name,
            "eligible": quality == "sufficient",
            "forecast_data_quality": quality,
            "can_forecast": quality != "insufficient",
            "estimated_month_total": estimate if quality != "insufficient" else None,
            "spent_so_far_this_month": current,
            "projected_remaining_expense": (
                max(estimate - current, 0)
                if quality != "insufficient"
                else None
            ),
            "optimization_history_sufficient": optimization_sufficient,
            "optimization_baseline_type": baseline_type,
            "optimization_history_reasons": [] if optimization_sufficient else ["Riwayat terlalu singkat"],
            "optimization_comparison_days": 20,
            "optimization_current_spending": current,
            "optimization_historical_normal": normal,
            "optimization_excess": excess,
        }

    def _recommend(
        self,
        categories: list[dict[str, object]],
        *,
        income: int,
        candidates: dict[str, bool] | None = None,
        selected_categories: list[str] | None = None,
        goals: list[dict[str, object]] | None = None,
        estimated_balance: int = 1_000,
        spending_limit_status: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run Recommendation V1 with a precomputed Financial Outlook fixture."""

        return self.service.get_recommendations(
            financial_outlook={
                "current_balance": estimated_balance + 500,
                "projected_selected_expense": 500,
                "estimated_balance_after_selected_spending": estimated_balance,
                "selected_categories": selected_categories or [],
            },
            expense_forecast={
                "as_of": self.TODAY,
                "categories": categories,
                "eligible_categories": [
                    item for item in categories if item["eligible"]
                ],
                "selected_categories": selected_categories or [],
            },
            goal_forecast={"goals": goals or []},
            saving_candidates=candidates or {},
            spending_limit_status=spending_limit_status,
        )

    def test_eligible_saving_candidate_can_be_recommended(self) -> None:
        """A forecast-ready approved category uses positive excess only."""

        result = self._recommend(
            [self._category("Makan", estimate=500, current=300, normal=100)],
            income=100,
            candidates={"Makan": True},
            selected_categories=["Makan"],
        )

        self.assertEqual(result["candidate_analysis"][0]["saving_capacity"], 200)
        self.assertEqual(
            result["category_recommendations"][0]["suggested_reduction"],
            200,
        )
        handoff = result["scenario_handoff"]["category_adjustments"][0]
        self.assertEqual(handoff["category"], "Makan")
        self.assertEqual(handoff["suggested_reduction"], 200)
        self.assertEqual(handoff["saving_capacity"], 200)
        self.assertEqual(handoff["source"], "recommendation_v1")

    def test_limited_forecast_category_can_still_be_analyzed(self) -> None:
        """Optimization history, not Forecast quality, controls analysis."""

        result = self._recommend(
            [
                self._category(
                    "Transport",
                    estimate=400,
                    current=300,
                    normal=100,
                    quality="limited",
                )
            ],
            income=100,
            candidates={"Transport": True},
        )

        analysis = result["candidate_analysis"][0]
        self.assertEqual(analysis["forecast_data_quality"], "limited")
        self.assertEqual(analysis["analysis_status"], "ready")
        self.assertEqual(analysis["saving_capacity"], 200)

    def test_limited_optimization_baseline_remains_explicit(self) -> None:
        """Current-period fallback is analyzable without being historical data."""

        result = self._recommend(
            [
                self._category(
                    "Makan",
                    estimate=500,
                    current=300,
                    normal=100,
                    baseline_type="limited_current_period",
                )
            ],
            income=100,
            candidates={"Makan": True},
        )

        self.assertEqual(
            result["candidate_analysis"][0]["optimization_baseline_type"],
            "limited_current_period",
        )

    def test_forecast_selection_does_not_change_recommendations(self) -> None:
        """Recommendation must never consume Forecast presentation selection."""

        category = self._category("Makan", estimate=500, current=300, normal=100)
        selected = self._recommend(
            [category],
            income=100,
            candidates={"Makan": True},
            selected_categories=["Makan"],
        )
        unselected = self._recommend(
            [category],
            income=100,
            candidates={"Makan": True},
            selected_categories=[],
        )

        self.assertEqual(
            selected["category_recommendations"],
            unselected["category_recommendations"],
        )

    def test_global_outlook_is_the_only_financial_condition_input(self) -> None:
        """Legacy detail aliases cannot override the global Forecast condition."""

        result = self.service.get_recommendations(
            financial_outlook={
                "current_balance": 300,
                "global_projected_remaining_spending": 500,
                "global_estimated_balance": -200,
                "projected_selected_expense": 0,
                "estimated_balance_after_selected_spending": 300,
                "global_forecast_categories": [],
                "selected_categories": [],
            },
            expense_forecast={"as_of": self.TODAY, "categories": []},
            goal_forecast={"goals": []},
            saving_candidates={},
            spending_limit_status={"configured": False, "spending_risk": False},
        )

        self.assertTrue(result["balance_risk"])
        self.assertEqual(result["balance_shortfall"], 200)
        self.assertEqual(result["global_projected_remaining_spending"], 500)

    def test_disabled_saving_candidate_is_not_analyzed(self) -> None:
        """A false Saving Candidate preference prevents analysis and advice."""

        result = self._recommend(
            [self._category("Transport", estimate=400, current=300, normal=100)],
            income=100,
            candidates={"Transport": False},
        )

        self.assertEqual(result["candidate_analysis"], [])
        self.assertEqual(result["category_recommendations"], [])

    def test_insufficient_optimization_history_never_fabricates_advice(self) -> None:
        """Enabled candidates without sufficient history remain explainable only."""

        result = self._recommend(
            [
                self._category(
                    "Hiburan",
                    estimate=600,
                    current=500,
                    normal=None,
                    quality="limited",
                    optimization_sufficient=False,
                )
            ],
            income=100,
            candidates={"Hiburan": True},
        )

        analysis = result["candidate_analysis"][0]
        self.assertEqual(analysis["analysis_status"], "insufficient_history")
        self.assertEqual(analysis["saving_capacity"], 0)
        self.assertEqual(result["category_recommendations"], [])

    def test_enabled_candidate_without_category_history_is_explained(self) -> None:
        """A saved preference survives absent data as an explicit diagnostic."""

        result = self._recommend(
            [],
            income=100,
            candidates={"Tempat Tinggal": True},
        )

        analysis = result["candidate_analysis"][0]
        self.assertEqual(analysis["category"], "Tempat Tinggal")
        self.assertEqual(analysis["analysis_status"], "insufficient_history")
        self.assertEqual(analysis["saving_capacity"], 0)

    def test_positive_estimated_balance_has_no_legacy_cashflow_deficit(self) -> None:
        """Recommendation must not create a second income-minus-expense model."""

        categories = [
            self._category("Makan", estimate=1_000, current=700, normal=500),
            self._category("Transport", estimate=800, current=200, normal=100),
            self._category(
                "Belanja",
                estimate=500,
                current=50,
                normal=None,
                quality="insufficient",
                optimization_sufficient=False,
            ),
        ]
        result = self._recommend(categories, income=2_000)

        self.assertFalse(result["balance_risk"])
        self.assertEqual(result["balance_shortfall"], 0)
        self.assertNotIn("cashflow_deficit", result)
        self.assertNotIn("projected_cashflow", result)
        self.assertNotIn("projected_monthly_expense", result)

    def test_comparable_period_excess_and_zero_opportunity_are_explicit(self) -> None:
        """Capacity is current comparable spending minus historical normal only."""

        result = self._recommend(
            [
                self._category("Makan", estimate=500, current=300, normal=300),
                self._category("Transport", estimate=700, current=500, normal=200),
            ],
            income=100,
            candidates={"Makan": True, "Transport": True},
        )

        makan = next(
            item for item in result["candidate_analysis"] if item["category"] == "Makan"
        )
        transport = next(
            item for item in result["candidate_analysis"] if item["category"] == "Transport"
        )
        self.assertEqual(makan["optimization_excess"], 0)
        self.assertEqual(makan["saving_capacity"], 0)
        self.assertEqual(transport["optimization_excess"], 300)
        self.assertEqual(transport["saving_capacity"], 300)

    def test_reduction_is_bounded_and_partial_balance_shortfall_is_honest(self) -> None:
        """Recommendations cannot exceed real capacity or hide a shortfall."""

        result = self._recommend(
            [self._category("Makan", estimate=800, current=400, normal=100)],
            income=100,
            candidates={"Makan": True},
            estimated_balance=-700,
        )

        self.assertTrue(result["balance_risk"])
        self.assertEqual(result["balance_shortfall"], 700)
        self.assertEqual(result["potential_saving"], 300)
        self.assertEqual(result["category_recommendations"][0]["suggested_reduction"], 300)
        self.assertEqual(result["remaining_balance_shortfall"], 400)
        self.assertEqual(
            result["expected_estimated_balance_after_recommendation"],
            -400,
        )

    def test_goal_allocation_and_scenario_handoff_remain_compatible(self) -> None:
        """Unused bounded capacity still funds high-priority Goal gaps in order."""

        result = self._recommend(
            [self._category("Makan", estimate=300, current=400, normal=100)],
            income=1_000,
            candidates={"Makan": True},
            selected_categories=["Makan"],
            goals=[self._goal_forecast("goal-high", "high", required=500, pace=100)],
        )

        self.assertEqual(result["goal_recommendations"][0]["suggested_allocation"], 300)
        adjustment = result["scenario_handoff"]["category_adjustments"]
        self.assertEqual(adjustment[0]["category"], "Makan")
        self.assertEqual(result["scenario_handoff"]["source"], "recommendation_v1")

    def test_negative_estimated_balance_uses_outlook_shortfall(self) -> None:
        """A negative selected-spending Outlook triggers only Balance Risk."""

        result = self._recommend([], income=99_999, estimated_balance=-300)

        self.assertTrue(result["balance_risk"])
        self.assertEqual(result["balance_shortfall"], 300)
        self.assertEqual(result["remaining_balance_shortfall"], 300)

    def test_forecast_selection_controls_only_supplied_outlook_risk(self) -> None:
        """An unselected category cannot alter the already-derived Outlook risk."""

        categories = [
            self._category("Makan", estimate=500, current=300, normal=100),
            self._category("Transport", estimate=900, current=500, normal=100),
        ]
        makan_only = self._recommend(
            categories,
            income=0,
            candidates={"Transport": True},
            selected_categories=["Makan"],
            estimated_balance=200,
        )

        self.assertFalse(makan_only["balance_risk"])
        self.assertEqual(makan_only["balance_shortfall"], 0)
        self.assertEqual(
            makan_only["category_recommendations"][0]["category"],
            "Transport",
        )
        self.assertEqual(
            makan_only["scenario_handoff"]["category_adjustments"],
            [],
        )

    def test_goal_risk_uses_available_saving_after_balance_is_safe(self) -> None:
        """Risky Goals receive a bounded, scenario-compatible opportunity."""

        result = self._recommend(
            [self._category("Makan", estimate=500, current=400, normal=100)],
            income=0,
            candidates={"Makan": True},
            selected_categories=["Makan"],
            goals=[self._goal_forecast("goal-high", "high", required=500, pace=100)],
            estimated_balance=500,
        )

        self.assertFalse(result["balance_risk"])
        self.assertEqual(result["goal_recommendations"][0]["suggested_allocation"], 300)
        self.assertEqual(
            result["scenario_handoff"]["goal_allocations"][0]["amount"],
            300,
        )

    def test_unset_or_zero_spending_limit_disables_spending_risk(self) -> None:
        """An unconfigured preference cannot manufacture a Spending Risk."""

        result = self._recommend(
            [],
            income=0,
            spending_limit_status={
                "configured": False,
                "monthly_spending_limit": 0,
                "projected_tracked_spending": 9_999,
                "spending_risk": False,
                "spending_limit_gap": 0,
            },
        )

        self.assertFalse(result["spending_risk"])
        self.assertEqual(result["spending_limit_gap"], 0)

    def test_healthy_balance_can_have_spending_risk_only(self) -> None:
        """The planning-limit warning arrives before liquidity is exhausted."""

        result = self._recommend(
            [],
            income=0,
            estimated_balance=4_400,
            spending_limit_status={
                "configured": True,
                "monthly_spending_limit": 3_000,
                "projected_tracked_spending": 3_300,
                "spending_risk": True,
                "spending_limit_gap": 300,
            },
        )

        self.assertFalse(result["balance_risk"])
        self.assertTrue(result["spending_risk"])
        self.assertEqual(result["spending_limit_gap"], 300)
        self.assertEqual(result["status"], "spending_risk")

    def test_spending_risk_reduction_is_bounded_and_reports_remaining_gap(self) -> None:
        """Only real Saving Candidate capacity can reduce a limit warning."""

        result = self._recommend(
            [self._category("Makan", estimate=600, current=350, normal=100)],
            income=0,
            candidates={"Makan": True},
            selected_categories=["Makan"],
            spending_limit_status={
                "configured": True,
                "monthly_spending_limit": 3_000,
                "projected_tracked_spending": 3_650,
                "spending_risk": True,
                "spending_limit_gap": 650,
            },
        )

        self.assertEqual(result["applied_saving"], 250)
        self.assertEqual(result["remaining_spending_limit_gap"], 400)
        self.assertEqual(
            result["category_recommendations"][0]["suggested_reduction"],
            250,
        )

    def test_recommendation_is_non_persistent_and_settings_preference_persists(self) -> None:
        """Never mutate inputs and persist only explicit local app preferences."""

        categories = [self._category("Makan", estimate=500, current=300, normal=100)]
        goals = [self._goal_forecast("goal-high", "high", required=500, pace=100)]
        categories_before = deepcopy(categories)
        goals_before = deepcopy(goals)
        self._recommend(categories, income=100, candidates={"Makan": True}, goals=goals)
        self.assertEqual(categories, categories_before)
        self.assertEqual(goals, goals_before)

        with TemporaryDirectory() as temporary_directory:
            storage_path = Path(temporary_directory) / "settings.json"
            worksheet = FakeSettingsWorksheet()
            settings = SettingsService(storage_path, worksheet)
            self.assertEqual(settings.get_saving_candidates(["Makan"]), {"Makan": False})
            settings.save_saving_candidates({"Makan": True, "Transport": False})
            self.assertEqual(
                SettingsService(storage_path, worksheet).get_saving_candidates(
                    ["Makan", "Transport"]
                ),
                {"Makan": True, "Transport": False},
            )
            self.assertEqual(
                SettingsService(storage_path, worksheet).get_saving_candidates(
                    ["Makan", "Transport", "Belanja"]
                ),
                {"Makan": True, "Transport": False, "Belanja": False},
            )

    @staticmethod
    def _goal_forecast(
        goal_id: str,
        priority: str,
        *,
        required: int,
        pace: int,
    ) -> dict[str, object]:
        """Build one risky Forecast V2 Goal result fixture."""

        goal = Goal(
            goal_id=goal_id,
            account_id="account-1",
            target_amount=10_000,
            deadline="2026-12-31",
            priority=priority,
            status="active",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        return {
            "goal": goal,
            "health": "Off Track",
            "required_monthly_contribution": required,
            "contribution_pace": {
                "is_sufficient": True,
                "monthly_amount": pace,
                "months": 2,
            },
        }


if __name__ == "__main__":
    unittest.main()
