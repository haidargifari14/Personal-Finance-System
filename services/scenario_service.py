"""Pure, non-persistent monthly Scenario Simulator calculations."""

from __future__ import annotations

from datetime import date, timedelta
from math import ceil, isfinite
from typing import Mapping, Sequence

from services.forecast_service import ForecastService
from services.goal_service import GoalService


class ScenarioService:
    """Calculate hypothetical spending and Goal outcomes from loaded forecasts."""

    def simulate(
        self,
        *,
        outlook: Mapping[str, object],
        goal_forecast: Mapping[str, object],
        adjustments: Sequence[Mapping[str, object]] = (),
        goal_allocations: Mapping[str, int | float] | None = None,
    ) -> dict[str, object]:
        """Return a scenario without reading or mutating financial data.

        Args:
            outlook: A previously calculated Forecast V2 Financial Outlook.
            goal_forecast: A previously calculated Goal Forecast result.
            adjustments: Per-category amount or percentage reductions.
            goal_allocations: Hypothetical monthly allocations keyed by Goal ID.

        Raises:
            ValueError: If an adjustment or Goal allocation is invalid.
        """

        global_categories = {
            str(item["category"]): item
            for item in outlook.get(
                "global_forecast_categories",
                outlook.get("selected_categories", []),
            )
        }
        normalized_adjustments = self._normalize_adjustments(
            adjustments,
            global_categories,
        )
        category_impacts = self._build_category_impacts(
            global_categories,
            normalized_adjustments,
        )
        baseline_spending = int(
            outlook.get(
                "global_projected_remaining_spending",
                outlook.get("projected_selected_expense", 0),
            )
        )
        scenario_spending = sum(
            int(item["scenario_future_expense"])
            for item in category_impacts
        )
        potential_saving = baseline_spending - scenario_spending
        current_balance = int(outlook.get("current_balance", 0))
        baseline_balance = int(
            outlook.get(
                "global_estimated_balance",
                outlook.get(
                    "estimated_balance_after_selected_spending",
                    current_balance - baseline_spending,
                ),
            )
        )
        scenario_balance = current_balance - scenario_spending
        balance_improvement = scenario_balance - baseline_balance
        improvement_percentage = (
            None
            if baseline_balance == 0
            else (balance_improvement / abs(baseline_balance)) * 100
        )
        allocations = self._normalize_goal_allocations(
            goal_allocations or {},
            goal_forecast,
            potential_saving,
        )
        as_of = self._as_date(outlook.get("as_of"))
        limit_status = dict(outlook.get("monthly_spending_limit_status", {}))
        monthly_limit = int(limit_status.get("monthly_spending_limit", 0) or 0)
        baseline_normalized_spending = int(
            limit_status.get(
                "projected_normalized_monthly_spending",
                limit_status.get("projected_tracked_spending", 0),
            )
        )
        scenario_normalized_spending = max(
            baseline_normalized_spending - potential_saving,
            0,
        )
        limit_configured = bool(limit_status.get("configured", False))
        scenario_spending_risk = (
            limit_configured and scenario_normalized_spending > monthly_limit
        )
        return {
            "as_of": as_of,
            "current_balance": current_balance,
            "baseline_projected_remaining_spending": baseline_spending,
            "scenario_projected_remaining_spending": scenario_spending,
            "baseline_projected_normalized_monthly_spending": (
                baseline_normalized_spending
            ),
            "scenario_projected_normalized_monthly_spending": (
                scenario_normalized_spending
            ),
            "monthly_spending_limit": monthly_limit,
            "monthly_spending_limit_configured": limit_configured,
            "baseline_spending_risk": bool(limit_status.get("spending_risk", False)),
            "scenario_spending_risk": scenario_spending_risk,
            "baseline_spending_limit_gap": int(
                limit_status.get("spending_limit_gap", 0) or 0
            ),
            "scenario_spending_limit_gap": (
                scenario_normalized_spending - monthly_limit
                if scenario_spending_risk
                else 0
            ),
            "potential_saving": potential_saving,
            "baseline_estimated_balance": baseline_balance,
            "scenario_estimated_balance": scenario_balance,
            "balance_improvement": balance_improvement,
            "balance_improvement_percentage": improvement_percentage,
            "category_impacts": category_impacts,
            "total_goal_allocation": sum(allocations.values()),
            "unallocated_saving": potential_saving - sum(allocations.values()),
            "goal_allocations": allocations,
            "goal_impacts": self._build_goal_impacts(
                goal_forecast,
                allocations,
                as_of,
            ),
            "baseline_trajectory": list(outlook.get("balance_trajectory", [])),
            "scenario_trajectory": self._build_scenario_trajectory(
                current_balance,
                category_impacts,
                as_of,
            ),
        }

    @staticmethod
    def _normalize_adjustments(
        adjustments: Sequence[Mapping[str, object]],
        selected: Mapping[str, Mapping[str, object]],
    ) -> dict[str, dict[str, object]]:
        """Validate and normalize user-entered category reductions."""

        normalized: dict[str, dict[str, object]] = {}
        for adjustment in adjustments:
            category = str(adjustment.get("category") or "").strip()
            if category not in selected:
                raise ValueError("Pilih hanya kategori yang memiliki Forecast aktif.")
            if category in normalized:
                raise ValueError(f"Penyesuaian kategori {category} dibuat lebih dari sekali.")
            mode = str(adjustment.get("mode") or "amount").lower()
            if mode not in {"amount", "percentage"}:
                raise ValueError("Mode pengurangan harus nominal atau persentase.")
            value = ScenarioService._non_negative_number(adjustment.get("value"))
            baseline = int(selected[category]["projected_remaining_expense"])
            if mode == "amount" and value > baseline:
                raise ValueError(
                    f"Pengurangan {category} tidak boleh melebihi proyeksi Rp{baseline:,.0f}."
                )
            if mode == "percentage" and value > 100:
                raise ValueError("Persentase pengurangan tidak boleh lebih dari 100%.")
            saving = int(round(baseline * value / 100)) if mode == "percentage" else int(value)
            normalized[category] = {"mode": mode, "value": value, "saving": saving}
        return normalized

    @staticmethod
    def _build_category_impacts(
        selected: Mapping[str, Mapping[str, object]],
        adjustments: Mapping[str, Mapping[str, object]],
    ) -> list[dict[str, object]]:
        """Build one independently calculated impact for every selected category."""

        impacts = []
        for category, forecast in selected.items():
            baseline = int(forecast["projected_remaining_expense"])
            adjustment = adjustments.get(category, {})
            saving = int(adjustment.get("saving", 0))
            impacts.append(
                {
                    "category": category,
                    "baseline_future_expense": baseline,
                    "scenario_future_expense": baseline - saving,
                    "potential_saving": saving,
                    "mode": adjustment.get("mode", "amount"),
                    "value": adjustment.get("value", 0),
                    "forecast_data_quality": forecast.get("forecast_data_quality"),
                }
            )
        return impacts

    def _normalize_goal_allocations(
        self,
        allocations: Mapping[str, int | float],
        goal_forecast: Mapping[str, object],
        potential_saving: int,
    ) -> dict[str, int]:
        """Validate allocations against eligible active Goals and saving capacity."""

        eligible = {
            str(item["goal"].goal_id): item
            for item in goal_forecast.get("goals", [])
            if str(getattr(item["goal"], "status", "")).lower() == "active"
            and item.get("account") is not None
        }
        normalized: dict[str, int] = {}
        for goal_id, value in allocations.items():
            amount = int(self._non_negative_number(value))
            if goal_id not in eligible:
                raise ValueError("Pilih hanya Goal aktif dengan Account yang tersedia.")
            if amount:
                normalized[str(goal_id)] = amount
        total = sum(normalized.values())
        if total > potential_saving:
            raise ValueError("Total alokasi Goal tidak boleh melebihi Potential Saving.")
        return normalized

    def _build_goal_impacts(
        self,
        goal_forecast: Mapping[str, object],
        allocations: Mapping[str, int],
        today: date,
    ) -> list[dict[str, object]]:
        """Recalculate eligible Goal health and completion hypothetically."""

        impacts = []
        for summary in goal_forecast.get("goals", []):
            goal = summary["goal"]
            goal_id = str(goal.goal_id)
            if goal_id not in allocations:
                continue
            if str(goal.status).lower() != "active" or summary.get("account") is None:
                continue
            allocation = allocations[goal_id]
            current = int(summary["current_progress"])
            simulated_current = current + allocation
            remaining = max(int(goal.target_amount) - simulated_current, 0)
            required = GoalService._required_monthly_contribution(
                remaining,
                GoalService._parse_deadline(goal.deadline),
                today,
            )
            pace = dict(summary["contribution_pace"])
            baseline_pace = pace.get("monthly_amount")
            baseline_monthly = float(baseline_pace) if isinstance(baseline_pace, (int, float)) else 0.0
            simulated_pace = baseline_monthly + allocation
            simulated_pace_data = {
                "is_sufficient": bool(pace.get("is_sufficient")) or allocation > 0,
                "monthly_amount": simulated_pace,
                "months": pace.get("months", 0),
            }
            deadline = GoalService._parse_deadline(goal.deadline)
            health = GoalService._calculate_health(
                current=simulated_current,
                target=int(goal.target_amount),
                deadline=deadline,
                reference_date=today,
                required_monthly=required,
                pace=simulated_pace_data,
            )
            completion, label = self._projected_completion(
                remaining,
                simulated_pace,
                bool(simulated_pace_data["is_sufficient"]),
                today,
            )
            if deadline is None and completion is not None:
                health = "No Deadline / Pace Available"
            gap = max(float(required or 0) - simulated_pace, 0)
            impacts.append(
                {
                    "goal": goal,
                    "account": summary["account"],
                    "allocation": allocation,
                    "baseline_health": summary["health"],
                    "scenario_health": health,
                    "baseline_completion": summary["projected_completion_label"],
                    "scenario_completion": label,
                    "scenario_completion_date": completion,
                    "baseline_monthly_pace": baseline_pace,
                    "scenario_monthly_pace": simulated_pace,
                    "simulated_current_progress": simulated_current,
                    "remaining_amount": remaining,
                    "required_monthly_contribution": required,
                    "remaining_contribution_gap": gap,
                }
            )
        return impacts

    @staticmethod
    def _projected_completion(
        remaining: int,
        monthly_pace: float,
        pace_available: bool,
        today: date,
    ) -> tuple[date | None, str]:
        """Reuse Goal Forecast completion semantics for simulated pace."""

        if remaining == 0:
            return None, "Already achieved"
        if not pace_available:
            return None, "Insufficient Allocation History"
        if monthly_pace <= 0:
            return None, "Unavailable (non-positive pace)"
        completion = ForecastService._add_months(today, ceil(remaining / monthly_pace))
        return completion, completion.strftime("%d %b %Y")

    @staticmethod
    def _build_scenario_trajectory(
        current_balance: int,
        category_impacts: Sequence[Mapping[str, object]],
        today: date,
    ) -> list[dict[str, object]]:
        """Create the scenario line using the Forecast V2 daily distribution."""

        remaining_days = ForecastService._remaining_days_in_month(today)
        trajectory = [{"date": today, "estimated_balance": current_balance}]
        daily_spending = [0] * remaining_days
        for impact in category_impacts:
            daily = ForecastService.distribute_projection_over_remaining_days(
                int(impact["scenario_future_expense"]),
                remaining_days,
            )
            for index, amount in enumerate(daily):
                daily_spending[index] += amount
        cumulative = 0
        for index, amount in enumerate(daily_spending, start=1):
            cumulative += amount
            trajectory.append(
                {
                    "date": today + timedelta(days=index),
                    "estimated_balance": current_balance - cumulative,
                }
            )
        return trajectory

    @staticmethod
    def _non_negative_number(value: object) -> float:
        """Return a finite non-negative numeric scenario input."""

        if isinstance(value, bool):
            raise ValueError("Nilai Scenario harus berupa angka.")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("Nilai Scenario harus berupa angka.") from error
        if not isfinite(number) or number < 0:
            raise ValueError("Nilai Scenario tidak boleh negatif.")
        return number

    @staticmethod
    def _as_date(value: object) -> date:
        """Keep scenario calculations aligned with the loaded Forecast date."""

        if isinstance(value, date):
            return value
        raise ValueError("Tanggal Forecast tidak valid untuk Scenario.")
