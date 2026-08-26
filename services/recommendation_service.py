"""Deterministic, non-persistent Recommendation Engine V1."""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from models.goal import Goal


class RecommendationService:
    """Allocate user-approved optimization capacity to current financial issues."""

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def get_recommendations(
        self,
        *,
        financial_outlook: Mapping[str, object],
        expense_forecast: Mapping[str, object],
        goal_forecast: Mapping[str, object],
        saving_candidates: Mapping[str, bool],
        spending_limit_status: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Return explainable recommendations without persisting financial data.

        Financial Outlook is the only future-balance source. Saving Candidate
        analysis remains independent from the detail-inspection selection.
        """

        as_of = expense_forecast["as_of"]
        if not isinstance(as_of, date):
            raise ValueError("Forecast reference date is required.")
        current_balance = int(financial_outlook["current_balance"])
        global_projected_remaining_spending = int(
            financial_outlook.get(
                "global_projected_remaining_spending",
                financial_outlook["projected_selected_expense"],
            )
        )
        estimated_balance = int(
            financial_outlook.get(
                "global_estimated_balance",
                financial_outlook["estimated_balance_after_selected_spending"],
            )
        )
        balance_shortfall = max(-estimated_balance, 0)
        limit_status = dict(spending_limit_status or {})
        spending_risk = bool(limit_status.get("spending_risk", False))
        spending_limit_gap = (
            int(limit_status.get("spending_limit_gap", 0)) if spending_risk else 0
        )
        categories = self._build_candidates(
            expense_forecast["categories"],
            saving_candidates,
        )
        category_recommendations, applied_saving = (
            self._build_spending_recommendations(
                categories,
                balance_shortfall,
                spending_limit_gap,
            )
        )
        remaining_shortfall = max(balance_shortfall - applied_saving, 0)
        remaining_spending_limit_gap = max(spending_limit_gap - applied_saving, 0)
        goal_recommendations = []
        if remaining_shortfall == 0 and remaining_spending_limit_gap == 0:
            goal_recommendations = self._allocate_goal_gaps(
                goal_forecast["goals"],
                applied_saving,
            )
        handoff = self._build_scenario_handoff(
            category_recommendations,
            goal_recommendations,
            financial_outlook.get(
                "global_forecast_categories",
                financial_outlook.get("selected_categories", []),
            ),
        )
        total_potential_saving = sum(
            int(item["saving_capacity"])
            for item in categories
            if item["analysis_status"] == "ready"
        )
        return {
            "status": self._status(
                balance_shortfall,
                spending_limit_gap,
                category_recommendations,
                goal_recommendations,
            ),
            "as_of": as_of,
            "current_balance": current_balance,
            "global_projected_remaining_spending": global_projected_remaining_spending,
            "projected_selected_expense": global_projected_remaining_spending,
            "global_estimated_balance": estimated_balance,
            "estimated_balance_after_selected_spending": estimated_balance,
            "balance_risk": balance_shortfall > 0,
            "balance_shortfall": balance_shortfall,
            "spending_limit_status": limit_status,
            "spending_risk": spending_risk,
            "spending_limit_gap": spending_limit_gap,
            "candidate_analysis": categories,
            "category_recommendations": category_recommendations,
            "potential_saving": total_potential_saving,
            "applied_saving": applied_saving,
            "remaining_balance_shortfall": remaining_shortfall,
            "remaining_spending_limit_gap": remaining_spending_limit_gap,
            "expected_estimated_balance_after_recommendation": (
                estimated_balance + applied_saving
            ),
            "goal_recommendations": goal_recommendations,
            "remaining_saving_capacity": max(
                total_potential_saving - applied_saving,
                0,
            ),
            "scenario_handoff": handoff,
            "message": self._message(
                balance_shortfall,
                spending_limit_gap,
                categories,
                category_recommendations,
                remaining_shortfall,
                remaining_spending_limit_gap,
                goal_recommendations,
            ),
        }

    @staticmethod
    def _build_candidates(
        forecast_categories: Sequence[Mapping[str, object]],
        saving_candidates: Mapping[str, bool],
    ) -> list[dict[str, object]]:
        """Build Saving Candidate analysis from independent optimization history."""

        results = []
        for category in forecast_categories:
            name = str(category["category"])
            if not bool(saving_candidates.get(name, False)):
                continue
            history_sufficient = bool(
                category.get("optimization_history_sufficient", False)
            )
            current_spending = category.get("optimization_current_spending")
            historical_normal = category.get("optimization_historical_normal")
            excess = category.get("optimization_excess")
            ready = (
                history_sufficient
                and isinstance(current_spending, int)
                and isinstance(historical_normal, int)
                and isinstance(excess, int)
            )
            results.append(
                {
                    "category": name,
                    "saving_candidate": True,
                    "forecast_data_quality": str(
                        category.get("forecast_data_quality", "insufficient")
                    ),
                    "optimization_baseline_type": str(
                        category.get("optimization_baseline_type", "insufficient")
                    ),
                    "optimization_history_sufficient": history_sufficient,
                    "optimization_history_reasons": list(
                        category.get("optimization_history_reasons", [])
                    ),
                    "comparison_days": int(
                        category.get("optimization_comparison_days", 0)
                    ),
                    "current_comparable_spending": current_spending,
                    "historical_normal_comparable_spending": historical_normal,
                    "optimization_excess": excess,
                    "saving_capacity": max(int(excess), 0) if ready else 0,
                    "analysis_status": "ready" if ready else "insufficient_history",
                }
            )
        known_categories = {str(item["category"]) for item in forecast_categories}
        for name, enabled in saving_candidates.items():
            if not bool(enabled) or str(name) in known_categories:
                continue
            results.append(
                {
                    "category": str(name),
                    "saving_candidate": True,
                    "forecast_data_quality": "no_data",
                    "optimization_baseline_type": "insufficient",
                    "optimization_history_sufficient": False,
                    "optimization_history_reasons": [
                        "Belum ada riwayat transaksi expense untuk kategori ini"
                    ],
                    "comparison_days": 0,
                    "current_comparable_spending": None,
                    "historical_normal_comparable_spending": None,
                    "optimization_excess": None,
                    "saving_capacity": 0,
                    "analysis_status": "insufficient_history",
                }
            )
        return sorted(
            results,
            key=lambda item: (
                item["analysis_status"] != "ready",
                -int(item["saving_capacity"]),
                str(item["category"]),
            ),
        )

    @staticmethod
    def _build_spending_recommendations(
        categories: Sequence[Mapping[str, object]],
        balance_shortfall: int,
        spending_limit_gap: int,
    ) -> tuple[list[dict[str, object]], int]:
        """Recommend every positive, history-backed saving opportunity.

        The resulting reductions improve the global Financial Outlook. They
        never derive a second future model from monthly income.
        """

        allocations = []
        applied_saving = 0
        for category in categories:
            if category["analysis_status"] != "ready":
                continue
            capacity = int(category["saving_capacity"])
            if capacity <= 0:
                continue
            reduction = capacity
            applied_saving += reduction
            name = str(category["category"])
            allocations.append(
                {
                    **category,
                    "suggested_reduction": reduction,
                    "remaining_balance_shortfall": max(
                        balance_shortfall - applied_saving,
                        0,
                    ),
                    "remaining_spending_limit_gap": max(
                        spending_limit_gap - applied_saving,
                        0,
                    ),
                    "explanation": (
                        f"{name} spent {category['current_comparable_spending']} over "
                        f"the current comparable period versus its historical normal "
                        f"of {category['historical_normal_comparable_spending']}."
                    ),
                }
            )
        return allocations, applied_saving

    def _allocate_goal_gaps(
        self,
        goals: Sequence[Mapping[str, object]],
        available_saving: int,
    ) -> list[dict[str, object]]:
        """Allocate unlocked recommendation saving to risky Goals in priority order."""

        available = available_saving
        allocations = []
        for forecast in sorted(goals, key=self._goal_sort_key):
            if available <= 0:
                break
            goal = forecast["goal"]
            if not isinstance(goal, Goal) or goal.status != "active":
                continue
            if forecast["health"] not in {"At Risk", "Off Track"}:
                continue
            required = forecast["required_monthly_contribution"]
            pace = forecast["contribution_pace"]
            pace_amount = pace["monthly_amount"]
            if not isinstance(required, (int, float)) or not isinstance(
                pace_amount,
                (int, float),
            ):
                continue
            gap = max(round(float(required) - float(pace_amount)), 0)
            if gap == 0:
                continue
            allocation = min(gap, available)
            available -= allocation
            allocations.append(
                {
                    "goal_id": goal.goal_id,
                    "goal_priority": goal.priority,
                    "contribution_gap": gap,
                    "suggested_allocation": allocation,
                    "remaining_goal_gap": gap - allocation,
                    "expected_impact": (
                        "Closes the monthly pace gap."
                        if allocation == gap
                        else "Improves the monthly pace but does not close the gap."
                    ),
                }
            )
        return allocations

    def _goal_sort_key(self, forecast: Mapping[str, object]) -> tuple[int, date, str]:
        """Sort High, Medium, Low and then earliest deadline deterministically."""

        goal = forecast["goal"]
        if not isinstance(goal, Goal):
            return (99, date.max, "")
        return (
            self.PRIORITY_ORDER.get(goal.priority, 99),
            date.fromisoformat(goal.deadline) if goal.deadline else date.max,
            goal.goal_id,
        )

    @staticmethod
    def _build_scenario_handoff(
        category_recommendations: Sequence[Mapping[str, object]],
        goal_recommendations: Sequence[Mapping[str, object]],
        global_categories: Sequence[object],
    ) -> dict[str, object]:
        """Expose a valid non-persistent input contract for the simulator.

        A Saving Candidate may be independent from Forecast detail inspection.
        Only globally forecastable categories are safe to prefill into Scenario.
        """

        global_names = {
            str(item.get("category"))
            if isinstance(item, Mapping)
            else str(item)
            for item in global_categories
        }
        scenario_categories = [
            item
            for item in category_recommendations
            if str(item["category"]) in global_names
        ]
        scenario_saving = sum(
            int(item["suggested_reduction"])
            for item in scenario_categories
        )
        remaining_goal_allocation = scenario_saving
        scenario_goals = []
        for item in goal_recommendations:
            if remaining_goal_allocation <= 0:
                break
            allocation = min(
                int(item["suggested_allocation"]),
                remaining_goal_allocation,
            )
            if allocation <= 0:
                continue
            remaining_goal_allocation -= allocation
            scenario_goals.append({**item, "suggested_allocation": allocation})

        return {
            "source": "recommendation_v1",
            "category_adjustments": [
                {
                    "category": item["category"],
                    "adjustment_type": "reduce_expense",
                    "amount": item["suggested_reduction"],
                    "suggested_reduction": item["suggested_reduction"],
                    "saving_capacity": item["saving_capacity"],
                    "source": "recommendation_v1",
                }
                for item in scenario_categories
            ],
            "goal_allocations": [
                {
                    "goal_id": item["goal_id"],
                    "amount": item["suggested_allocation"],
                    "source": "recommendation_v1",
                }
                for item in scenario_goals
            ],
        }

    @staticmethod
    def _status(
        balance_shortfall: int,
        spending_limit_gap: int,
        categories: Sequence[Mapping[str, object]],
        goals: Sequence[Mapping[str, object]],
    ) -> str:
        """Classify the recommendation result without fabricating an action."""

        if balance_shortfall > 0:
            return "balance_risk"
        if spending_limit_gap > 0:
            return "spending_risk"
        if goals:
            return "goal_risk"
        if categories:
            return "optimization_opportunity"
        if balance_shortfall > 0 or spending_limit_gap > 0:
            return "no_opportunity"
        return "no_action"

    @staticmethod
    def _message(
        balance_shortfall: int,
        spending_limit_gap: int,
        candidate_analysis: Sequence[Mapping[str, object]],
        categories: Sequence[Mapping[str, object]],
        remaining_balance_shortfall: int,
        remaining_spending_limit_gap: int,
        goals: Sequence[Mapping[str, object]],
    ) -> str:
        """Return a concise user-readable result explanation."""

        if balance_shortfall > 0 and not categories:
            if candidate_analysis:
                return "Global projected spending may exceed available balance, but no positive reduction opportunity is available."
            return "No Saving Candidate is enabled for optimization analysis."
        if balance_shortfall > 0 and remaining_balance_shortfall > 0:
            return "Potential saving improves the global balance shortfall but does not fully solve it."
        if spending_limit_gap > 0 and not categories:
            if candidate_analysis:
                return "Projected normalized spending exceeds your Monthly Spending Limit, but no realistic reduction opportunity was detected."
            return "Projected normalized spending exceeds your Monthly Spending Limit, but no Saving Candidate is enabled."
        if spending_limit_gap > 0 and remaining_spending_limit_gap > 0:
            return "Potential saving reduces the Monthly Spending Limit gap but does not fully close it."
        if categories:
            if balance_shortfall > 0:
                return "Suggested reductions can restore a non-negative global estimated balance."
            if spending_limit_gap > 0:
                return "Suggested reductions can bring projected normalized spending closer to your Monthly Spending Limit."
            if goals:
                return "Potential saving can improve Goal contribution pace."
            return "Spending optimization opportunities were detected without a balance risk."
        if goals:
            return "Available saving can improve Goal contribution pace."
        return "No immediate spending reduction or Goal pace improvement is required."
