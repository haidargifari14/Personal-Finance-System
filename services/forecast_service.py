"""Forecast V2 service for category expenses and Account-linked Goals."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from math import ceil
from typing import Mapping, Sequence

import pandas as pd

from services.account_service import AccountService
from services.analytics_service import AnalyticsService
from services.goal_service import GoalService
from services.transaction_schema import (
    normalize_expense_metadata,
    normalized_monthly_expense_contribution,
)


class ForecastService:
    """Build transparent, deterministic Forecast V2 results for the dashboard."""

    MINIMUM_COVERAGE_DAYS = 14
    MINIMUM_TRANSACTION_COUNT = 10
    MINIMUM_ACTIVE_DAYS = 7
    MINIMUM_BASIC_COVERAGE_DAYS = 3
    MINIMUM_BASIC_TRANSACTION_COUNT = 3
    MINIMUM_BASIC_ACTIVE_DAYS = 2
    MINIMUM_OPTIMIZATION_COVERAGE_DAYS = 7
    MINIMUM_OPTIMIZATION_TRANSACTION_COUNT = 5
    MINIMUM_OPTIMIZATION_ACTIVE_DAYS = 4
    WINDOW_THRESHOLDS = ((90, 90), (60, 60), (30, 30))

    def __init__(
        self,
        analytics_service: AnalyticsService | None = None,
        account_service: AccountService | None = None,
        goal_service: GoalService | None = None,
    ) -> None:
        """Initialize V2 dependencies while preserving service boundaries."""

        self._analytics_service = analytics_service or AnalyticsService()
        sheet_service = getattr(self._analytics_service, "sheet_service", None)
        self._account_service = account_service or AccountService(sheet_service)
        self._goal_service = goal_service or GoalService(sheet_service)

    def get_expense_forecast(
        self,
        reference_date: date | None = None,
    ) -> dict[str, object]:
        """Return per-category eligibility and current-month expense forecasts."""

        today = reference_date or date.today()
        expenses = self._get_expense_transactions(today)
        actual_expense_so_far = (
            self._actual_month_expense(expenses, today) if not expenses.empty else 0
        )
        normalized_monthly_spending_so_far = (
            self._actual_month_normalized_spending(expenses, today)
            if not expenses.empty
            else 0
        )
        categorized_expenses = expenses[expenses["category"].ne("")].copy()
        categories = [
            self._build_category_forecast(str(category), data, today)
            for category, data in categorized_expenses.groupby("category", sort=True)
        ]
        categories.sort(key=self._category_sort_key)
        classification_breakdown = self._classification_breakdown(expenses, today)
        return {
            "as_of": today,
            "actual_expense_so_far": actual_expense_so_far,
            "normalized_monthly_spending_so_far": normalized_monthly_spending_so_far,
            "classification_breakdown": classification_breakdown,
            "categories": categories,
            "eligible_categories": [
                item for item in categories if bool(item["eligible"])
            ],
            "ineligible_categories": [
                item for item in categories if not bool(item["eligible"])
            ],
            "forecastable_categories": [
                item for item in categories if bool(item["can_forecast"])
            ],
            "limited_forecast_categories": [
                item
                for item in categories
                if item["forecast_data_quality"] == "limited"
            ],
            "insufficient_forecast_categories": [
                item
                for item in categories
                if item["forecast_data_quality"] == "insufficient"
            ],
            "optimization_categories": [
                item
                for item in categories
                if bool(item["optimization_history_sufficient"])
            ],
        }

    def get_financial_outlook(
        self,
        selected_categories: Sequence[str] | None = None,
        reference_date: date | None = None,
        expense_forecast: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Return the global future-spending and active-Account balance outlook.

        Args:
            selected_categories: Deprecated presentation-only detail selection.
                It is accepted for backward compatibility and never affects the
                global Financial Outlook.
            reference_date: Optional Forecast V2 reference date.
            expense_forecast: Already-loaded Forecast V2 result to avoid duplicate work.
        """

        expense_result = expense_forecast or self.get_expense_forecast(reference_date)
        del selected_categories
        global_forecasts = list(expense_result["forecastable_categories"])
        global_projected_remaining_spending = int(
            sum(
                int(item["projected_remaining_expense"])
                for item in global_forecasts
            )
        )
        current_balance = self._get_active_account_balance()
        estimated_balance = current_balance - global_projected_remaining_spending
        return {
            "as_of": expense_result["as_of"],
            "current_balance": current_balance,
            "global_projected_remaining_spending": global_projected_remaining_spending,
            "projected_selected_expense": global_projected_remaining_spending,
            "global_estimated_balance": estimated_balance,
            "estimated_balance_after_selected_spending": estimated_balance,
            "balance_risk": estimated_balance < 0,
            "balance_trajectory": self._build_balance_trajectory(
                current_balance,
                global_forecasts,
                expense_result["as_of"],
            ),
            "global_forecast_categories": global_forecasts,
            "selected_categories": global_forecasts,
            "global_category_inclusion_rules": (
                "Includes sufficient categories and limited categories with a "
                "usable basic forecast; excludes insufficient categories."
            ),
            "expense_forecast": expense_result,
        }

    @staticmethod
    def get_monthly_spending_limit_status(
        *,
        monthly_spending_limit: int,
        expense_forecast: Mapping[str, object],
        financial_outlook: Mapping[str, object],
    ) -> dict[str, object]:
        """Return an in-memory monthly Spending Limit status from Forecast data.

        Normalized spending comes from the current-month Expense snapshot in
        ``expense_forecast``. All globally forecastable categories contribute
        future projected spending through ``financial_outlook``. Future
        category projections are treated as Normal because they do not map to
        individual classified future transactions.
        """

        if isinstance(monthly_spending_limit, bool):
            limit = 0
        else:
            try:
                limit = max(int(monthly_spending_limit), 0)
            except (TypeError, ValueError):
                limit = 0
        normalized_expense = int(
            expense_forecast.get(
                "normalized_monthly_spending_so_far",
                expense_forecast.get("actual_expense_so_far", 0),
            )
        )
        projected_remaining = int(
            financial_outlook.get(
                "global_projected_remaining_spending",
                financial_outlook.get("projected_selected_expense", 0),
            )
        )
        projected_normalized_monthly_spending = (
            normalized_expense + projected_remaining
        )
        configured = limit > 0
        spending_risk = configured and projected_normalized_monthly_spending > limit
        return {
            "configured": configured,
            "monthly_spending_limit": limit,
            "actual_expense_so_far": int(
                expense_forecast.get("actual_expense_so_far", 0)
            ),
            "normalized_monthly_spending_so_far": normalized_expense,
            "global_projected_remaining_spending": projected_remaining,
            "projected_remaining_selected_spending": projected_remaining,
            "projected_normalized_monthly_spending": (
                projected_normalized_monthly_spending
            ),
            "projected_tracked_spending": projected_normalized_monthly_spending,
            "spending_limit_usage_percent": (
                (projected_normalized_monthly_spending / limit) * 100
                if configured
                else None
            ),
            "spending_risk": spending_risk,
            "spending_limit_gap": (
                projected_normalized_monthly_spending - limit
                if spending_risk
                else 0
            ),
        }

    def get_actual_monthly_income(
        self,
        reference_date: date | None = None,
    ) -> int:
        """Return actual Income received in the current calendar month only."""

        today = reference_date or date.today()
        transactions = self._analytics_service.get_transactions(
            sort_by="Date",
            sort_order="Ascending",
        ).copy()
        if transactions.empty:
            return 0
        transactions["date"] = pd.to_datetime(transactions["date"])
        transactions["amount"] = pd.to_numeric(
            transactions["amount"],
            errors="coerce",
        ).fillna(0).astype(int)
        month_income = transactions[
            (transactions["date"].dt.year == today.year)
            & (transactions["date"].dt.month == today.month)
            & (transactions["date"].dt.date <= today)
            & (transactions["type"].astype(str).str.lower() == "income")
        ]
        return int(month_income["amount"].sum())

    def get_goal_forecast(
        self,
        reference_date: date | None = None,
    ) -> dict[str, object]:
        """Return Account-derived Goal Forecast V2 results without legacy goals."""

        today = reference_date or date.today()
        results = []
        for summary in self._goal_service.get_goal_summaries(today):
            goal = summary["goal"]
            if getattr(goal, "status", "") == "closed":
                continue
            results.append(self._build_goal_forecast(summary, today))
        return {"as_of": today, "goals": results}

    def _get_expense_transactions(self, today: date) -> pd.DataFrame:
        """Load only historical Expense Transactions through AnalyticsService."""

        transactions = self._analytics_service.get_transactions(
            transaction_type="expense",
            sort_by="Date",
            sort_order="Ascending",
        ).copy()
        if transactions.empty:
            return pd.DataFrame(columns=["date", "category", "amount", "type"])
        transactions["date"] = pd.to_datetime(transactions["date"])
        transactions["amount"] = pd.to_numeric(
            transactions["amount"],
            errors="coerce",
        ).fillna(0).astype(int)
        transactions["category"] = transactions["category"].astype(str).str.strip()
        metadata = transactions.apply(
            lambda record: normalize_expense_metadata(
                "expense",
                record.get("expense_type"),
                record.get("coverage_months"),
            ),
            axis=1,
            result_type="expand",
        )
        metadata.columns = ["expense_type", "coverage_months"]
        transactions[["expense_type", "coverage_months"]] = metadata
        transactions["normalized_monthly_contribution"] = transactions.apply(
            lambda record: normalized_monthly_expense_contribution(record),
            axis=1,
        )
        return transactions[
            (transactions["date"].dt.date <= today)
            & (transactions["type"].astype(str).str.lower() == "expense")
        ].copy()

    def _build_category_forecast(
        self,
        category: str,
        category_data: pd.DataFrame,
        today: date,
    ) -> dict[str, object]:
        """Calculate eligibility and one category's remaining-month forecast."""

        behavioral_data = category_data[
            category_data["expense_type"] == "normal"
        ].copy()
        raw_transaction_count = len(category_data)
        if behavioral_data.empty:
            return self._insufficient_category_forecast(
                category,
                category_data,
                today,
                ["Belum ada transaksi Normal untuk riwayat perilaku"],
            )

        history_start = behavioral_data["date"].min().date()
        history_end = behavioral_data["date"].max().date()
        coverage_days = (history_end - history_start).days + 1
        transaction_count = len(behavioral_data)
        active_days = behavioral_data["date"].dt.normalize().nunique()
        reasons = self._eligibility_reasons(
            coverage_days,
            transaction_count,
            active_days,
        )
        basic_reasons = self._basic_forecast_reasons(
            coverage_days,
            transaction_count,
            active_days,
        )
        if not reasons:
            forecast_data_quality = "sufficient"
        elif not basic_reasons:
            forecast_data_quality = "limited"
        else:
            forecast_data_quality = "insufficient"
        result: dict[str, object] = {
            "category": category,
            "eligible": not reasons,
            "ineligibility_reasons": reasons,
            "forecast_data_quality": forecast_data_quality,
            "can_forecast": forecast_data_quality != "insufficient",
            "limited_forecast_reasons": reasons if reasons else [],
            "historical_coverage_days": coverage_days,
            "transaction_count": transaction_count,
            "active_days": int(active_days),
            "raw_transaction_count": raw_transaction_count,
            "training_transaction_count": transaction_count,
            "training_spending": int(behavioral_data["amount"].sum()),
            "included_in_global_outlook": forecast_data_quality != "insufficient",
            "global_exclusion_reason": (
                None
                if forecast_data_quality != "insufficient"
                else "; ".join(basic_reasons)
            ),
            "historical_window_days": None,
            "historical_window_start": None,
            "historical_window_end": None,
            "average_daily_spending": None,
            "spent_so_far_this_month": self._actual_month_spending(category_data, today),
            "normalized_spending_so_far": self._actual_month_normalized_spending(
                category_data,
                today,
            ),
            "projected_remaining_expense": None,
            "estimated_month_total": None,
        }
        result.update(self._build_optimization_history(behavioral_data, today))
        if forecast_data_quality == "insufficient":
            return result

        window_days = (
            self._select_window_days(coverage_days)
            if not reasons
            else coverage_days
        )
        window_start = max(
            pd.Timestamp(history_start),
            pd.Timestamp(history_end) - pd.Timedelta(days=window_days - 1),
        )
        window_end = pd.Timestamp(history_end)
        window_data = behavioral_data[
            (behavioral_data["date"] >= window_start)
            & (behavioral_data["date"] <= window_end)
        ]
        average_daily_spending = int(window_data["amount"].sum()) / window_days
        projected_remaining = round(
            average_daily_spending * self._remaining_days_in_month(today)
        )
        spent_so_far = int(result["spent_so_far_this_month"])
        result.update(
            {
                "historical_window_days": window_days,
                "historical_window_start": window_start.date(),
                "historical_window_end": window_end.date(),
                "average_daily_spending": average_daily_spending,
                "projected_remaining_expense": projected_remaining,
                "estimated_month_total": spent_so_far + projected_remaining,
            }
        )
        return result

    def _insufficient_category_forecast(
        self,
        category: str,
        category_data: pd.DataFrame,
        today: date,
        reasons: list[str],
    ) -> dict[str, object]:
        """Return an auditable result when no Normal behavioral history exists."""

        raw_transaction_count = len(category_data)
        raw_coverage_days = 0
        if not category_data.empty:
            raw_coverage_days = (
                category_data["date"].max().date()
                - category_data["date"].min().date()
            ).days + 1
        result: dict[str, object] = {
            "category": category,
            "eligible": False,
            "ineligibility_reasons": reasons,
            "forecast_data_quality": "insufficient",
            "can_forecast": False,
            "limited_forecast_reasons": [],
            "historical_coverage_days": 0,
            "transaction_count": 0,
            "active_days": 0,
            "raw_transaction_count": raw_transaction_count,
            "training_transaction_count": 0,
            "training_spending": 0,
            "included_in_global_outlook": False,
            "global_exclusion_reason": "; ".join(reasons),
            "historical_window_days": None,
            "historical_window_start": None,
            "historical_window_end": None,
            "average_daily_spending": None,
            "spent_so_far_this_month": self._actual_month_spending(category_data, today),
            "normalized_spending_so_far": self._actual_month_normalized_spending(
                category_data,
                today,
            ),
            "projected_remaining_expense": None,
            "estimated_month_total": None,
            "raw_historical_coverage_days": raw_coverage_days,
        }
        result.update(
            self._insufficient_optimization_result(
                current_spending=int(
                    self._actual_month_normalized_spending(category_data, today)
                ),
                comparison_days=today.day,
                reasons=[*reasons],
            )
        )
        return result

    @staticmethod
    def _classification_breakdown(
        expenses: pd.DataFrame,
        today: date,
    ) -> dict[str, int]:
        """Return current-month classified expense facts for Forecast auditing."""

        if expenses.empty:
            return {
                "actual_cash_expense_this_month": 0,
                "normal_expense_contribution": 0,
                "periodic_raw_expense": 0,
                "periodic_monthly_equivalent": 0,
                "one_off_expense": 0,
                "one_off_excluded_amount": 0,
                "normalized_spending_so_far": 0,
            }
        current_month = expenses[
            (expenses["date"].dt.year == today.year)
            & (expenses["date"].dt.month == today.month)
        ]
        normal = current_month[current_month["expense_type"] == "normal"]
        periodic = current_month[current_month["expense_type"] == "periodic"]
        one_off = current_month[current_month["expense_type"] == "one-off"]
        return {
            "actual_cash_expense_this_month": int(current_month["amount"].sum()),
            "normal_expense_contribution": int(normal["amount"].sum()),
            "periodic_raw_expense": int(periodic["amount"].sum()),
            "periodic_monthly_equivalent": int(
                periodic["normalized_monthly_contribution"].sum()
            ),
            "one_off_expense": int(one_off["amount"].sum()),
            "one_off_excluded_amount": int(one_off["amount"].sum()),
            "normalized_spending_so_far": int(
                current_month["normalized_monthly_contribution"].sum()
            ),
        }

    def _build_optimization_history(
        self,
        category_data: pd.DataFrame,
        today: date,
    ) -> dict[str, object]:
        """Build a comparable-period baseline independent of Forecast selection.

        Recommendation compares spending through ``today`` with the historical
        normal for the same number of calendar days. The current month is
        excluded from the historical normal to avoid using current spending as
        its own baseline.
        """

        month_start = pd.Timestamp(date(today.year, today.month, 1))
        history = category_data[category_data["date"] < month_start]
        current_spending = self._actual_month_normalized_spending(category_data, today)
        if history.empty:
            return self._build_limited_current_period_baseline(
                category_data,
                today,
                current_spending,
            )

        history_start = history["date"].min().date()
        history_end = history["date"].max().date()
        coverage_days = (history_end - history_start).days + 1
        transaction_count = len(history)
        active_days = int(history["date"].dt.normalize().nunique())
        reasons = self._optimization_history_reasons(
            coverage_days,
            transaction_count,
            active_days,
        )
        normal = round(
            int(history["normalized_monthly_contribution"].sum())
            / coverage_days
            * today.day
        )
        return {
            "optimization_history_sufficient": not reasons,
            "optimization_baseline_type": "historical" if not reasons else "insufficient",
            "optimization_history_reasons": reasons,
            "optimization_historical_coverage_days": coverage_days,
            "optimization_transaction_count": transaction_count,
            "optimization_active_days": active_days,
            "optimization_comparison_days": today.day,
            "optimization_current_spending": current_spending,
            "optimization_historical_normal": normal if not reasons else None,
            "optimization_excess": (
                current_spending - normal if not reasons else None
            ),
        }

    def _build_limited_current_period_baseline(
        self,
        category_data: pd.DataFrame,
        today: date,
        total_current_spending: int,
    ) -> dict[str, object]:
        """Build a marked limited baseline from earlier current-period activity.

        When no previous-period data exists, the available current period is
        split into chronological halves. Earlier spending is normalized to the
        later half's calendar-day length, then compared to the later spending.
        This is deliberately lower-confidence than a multi-period baseline.
        """

        current_month = category_data[
            (category_data["date"].dt.year == today.year)
            & (category_data["date"].dt.month == today.month)
        ].copy()
        if current_month.empty:
            return self._insufficient_optimization_result(
                current_spending=total_current_spending,
                comparison_days=today.day,
                reasons=["Belum ada riwayat sebelum bulan berjalan"],
            )
        start = current_month["date"].min().date()
        end = current_month["date"].max().date()
        coverage_days = (end - start).days + 1
        transaction_count = len(current_month)
        active_days = int(current_month["date"].dt.normalize().nunique())
        reasons = self._eligibility_reasons(
            coverage_days,
            transaction_count,
            active_days,
        )
        if reasons:
            return self._insufficient_optimization_result(
                current_spending=total_current_spending,
                comparison_days=today.day,
                reasons=[
                    "Belum ada riwayat sebelum bulan berjalan",
                    *reasons,
                ],
                coverage_days=coverage_days,
                transaction_count=transaction_count,
                active_days=active_days,
            )

        earlier_days = coverage_days // 2
        recent_days = coverage_days - earlier_days
        split_date = pd.Timestamp(start) + pd.Timedelta(days=earlier_days)
        earlier = current_month[current_month["date"] < split_date]
        recent = current_month[current_month["date"] >= split_date]
        earlier_spending = int(earlier["normalized_monthly_contribution"].sum())
        recent_spending = int(recent["normalized_monthly_contribution"].sum())
        baseline = round(earlier_spending / earlier_days * recent_days)
        return {
            "optimization_history_sufficient": True,
            "optimization_baseline_type": "limited_current_period",
            "optimization_history_reasons": [
                "Menggunakan baseline terbatas dari periode berjalan"
            ],
            "optimization_historical_coverage_days": coverage_days,
            "optimization_transaction_count": transaction_count,
            "optimization_active_days": active_days,
            "optimization_comparison_days": recent_days,
            "optimization_current_spending": recent_spending,
            "optimization_historical_normal": baseline,
            "optimization_excess": recent_spending - baseline,
        }

    @staticmethod
    def _insufficient_optimization_result(
        *,
        current_spending: int,
        comparison_days: int,
        reasons: list[str],
        coverage_days: int = 0,
        transaction_count: int = 0,
        active_days: int = 0,
    ) -> dict[str, object]:
        """Return one explicit optimization empty state without fabrication."""

        return {
            "optimization_history_sufficient": False,
            "optimization_baseline_type": "insufficient",
            "optimization_history_reasons": reasons,
            "optimization_historical_coverage_days": coverage_days,
            "optimization_transaction_count": transaction_count,
            "optimization_active_days": active_days,
            "optimization_comparison_days": comparison_days,
            "optimization_current_spending": current_spending,
            "optimization_historical_normal": None,
            "optimization_excess": None,
        }

    @staticmethod
    def _build_balance_trajectory(
        current_balance: int,
        selected_forecasts: list[Mapping[str, object]],
        today: date,
    ) -> list[dict[str, object]]:
        """Project one selected-expense balance line through the current month."""

        remaining_days = ForecastService._remaining_days_in_month(today)
        trajectory = [
            {
                "date": today,
                "estimated_balance": current_balance,
                "projected_spending_today": 0,
                "cumulative_selected_spending": 0,
            }
        ]
        if remaining_days == 0:
            return trajectory

        daily_spending = [0] * remaining_days
        for forecast in selected_forecasts:
            projection = int(forecast["projected_remaining_expense"])
            category_spending = ForecastService.distribute_projection_over_remaining_days(
                projection,
                remaining_days,
            )
            for index, spending in enumerate(category_spending):
                daily_spending[index] += spending

        cumulative = 0
        for index, spending in enumerate(daily_spending, start=1):
            cumulative += spending
            trajectory.append(
                {
                    "date": today + timedelta(days=index),
                    "estimated_balance": current_balance - cumulative,
                    "projected_spending_today": spending,
                    "cumulative_selected_spending": cumulative,
                }
            )
        return trajectory

    @staticmethod
    def distribute_projection_over_remaining_days(
        projection: int,
        remaining_days: int,
    ) -> list[int]:
        """Distribute one future projection deterministically across days."""

        if remaining_days <= 0:
            return []
        quotient, remainder = divmod(int(projection), remaining_days)
        return [
            quotient + (1 if index < remainder else 0)
            for index in range(remaining_days)
        ]

    def _build_goal_forecast(
        self,
        summary: Mapping[str, object],
        today: date,
    ) -> dict[str, object]:
        """Add projected completion to GoalService's derived Goal summary."""

        goal = summary["goal"]
        current = summary["current_progress"]
        remaining = summary["remaining_amount"]
        pace = summary["contribution_pace"]
        health = str(summary["health"])
        result: dict[str, object] = {
            "goal": goal,
            "account": summary["account"],
            "current_progress": current,
            "remaining_amount": remaining,
            "progress_percent": summary["progress_percent"],
            "required_monthly_contribution": summary[
                "required_monthly_contribution"
            ],
            "contribution_pace": pace,
            "health": health,
            "projected_completion": None,
            "projected_completion_label": "Unavailable",
        }
        if current is None or remaining is None:
            result["projected_completion_label"] = "Account unavailable"
            return result
        if health == "Achieved":
            result["projected_completion_label"] = "Already achieved"
            return result
        if not bool(pace["is_sufficient"]):
            result["projected_completion_label"] = "Insufficient Allocation History"
            return result
        monthly_pace = float(pace["monthly_amount"])
        if monthly_pace <= 0:
            result["projected_completion_label"] = "Unavailable (non-positive pace)"
            return result
        months_needed = ceil(int(remaining) / monthly_pace)
        completion = self._add_months(today, months_needed)
        result["months_needed"] = months_needed
        result["projected_completion"] = completion
        result["projected_completion_label"] = completion.strftime("%d %b %Y")
        if getattr(goal, "deadline", None) is None:
            result["health"] = "No Deadline / Pace Available"
        return result

    def _get_active_account_balance(self) -> int:
        """Calculate system balance from active Account summaries only."""

        return int(
            self._account_service.get_current_balance_summary()["current_balance"]
        )

    @staticmethod
    def _eligibility_reasons(
        coverage_days: int,
        transaction_count: int,
        active_days: int,
    ) -> list[str]:
        """Return clear reasons when a category is too sparse to forecast."""

        reasons = []
        if coverage_days < ForecastService.MINIMUM_COVERAGE_DAYS:
            reasons.append("Coverage kurang dari 14 hari kalender")
        if transaction_count < ForecastService.MINIMUM_TRANSACTION_COUNT:
            reasons.append("Kurang dari 10 transaksi expense")
        if active_days < ForecastService.MINIMUM_ACTIVE_DAYS:
            reasons.append("Kurang dari 7 hari aktif")
        return reasons

    @staticmethod
    def _basic_forecast_reasons(
        coverage_days: int,
        transaction_count: int,
        active_days: int,
    ) -> list[str]:
        """Return reasons when even a low-confidence estimate is unsafe."""

        reasons = []
        if coverage_days < ForecastService.MINIMUM_BASIC_COVERAGE_DAYS:
            reasons.append("Coverage kurang dari 3 hari kalender")
        if transaction_count < ForecastService.MINIMUM_BASIC_TRANSACTION_COUNT:
            reasons.append("Kurang dari 3 transaksi expense")
        if active_days < ForecastService.MINIMUM_BASIC_ACTIVE_DAYS:
            reasons.append("Kurang dari 2 hari aktif")
        return reasons

    @staticmethod
    def _optimization_history_reasons(
        coverage_days: int,
        transaction_count: int,
        active_days: int,
    ) -> list[str]:
        """Return lightweight, deterministic requirements for optimization."""

        reasons = []
        if coverage_days < ForecastService.MINIMUM_OPTIMIZATION_COVERAGE_DAYS:
            reasons.append("Coverage optimasi kurang dari 7 hari kalender")
        if transaction_count < ForecastService.MINIMUM_OPTIMIZATION_TRANSACTION_COUNT:
            reasons.append("Kurang dari 5 transaksi riwayat")
        if active_days < ForecastService.MINIMUM_OPTIMIZATION_ACTIVE_DAYS:
            reasons.append("Kurang dari 4 hari aktif riwayat")
        return reasons

    @staticmethod
    def _category_sort_key(category: Mapping[str, object]) -> tuple[int, str]:
        """Keep sufficient, limited, then insufficient forecast data grouped."""

        quality_rank = {"sufficient": 0, "limited": 1, "insufficient": 2}
        return (
            quality_rank.get(str(category["forecast_data_quality"]), 99),
            str(category["category"]),
        )

    @classmethod
    def _select_window_days(cls, coverage_days: int) -> int:
        """Select the locked rolling historical window for one category."""

        for minimum_coverage, window_days in cls.WINDOW_THRESHOLDS:
            if coverage_days >= minimum_coverage:
                return window_days
        return coverage_days

    @staticmethod
    def _actual_month_spending(data: pd.DataFrame, today: date) -> int:
        """Return actual spending already recorded in today's calendar month."""

        current_month = data[
            (data["date"].dt.year == today.year)
            & (data["date"].dt.month == today.month)
        ]
        return int(current_month["amount"].sum())

    @staticmethod
    def _actual_month_expense(data: pd.DataFrame, today: date) -> int:
        """Return all actual current-month Expense, including uncategorized rows."""

        current_month = data[
            (data["date"].dt.year == today.year)
            & (data["date"].dt.month == today.month)
        ]
        return int(current_month["amount"].sum())

    @staticmethod
    def _actual_month_normalized_spending(data: pd.DataFrame, today: date) -> int:
        """Return classified current-month Expense for spending discipline only."""

        current_month = data[
            (data["date"].dt.year == today.year)
            & (data["date"].dt.month == today.month)
        ]
        return int(current_month["normalized_monthly_contribution"].sum())

    @staticmethod
    def _remaining_days_in_month(today: date) -> int:
        """Return future calendar days after today until the month closes."""

        return monthrange(today.year, today.month)[1] - today.day

    @staticmethod
    def _add_months(start: date, months: int) -> date:
        """Return an approximate month-normalized completion date."""

        month_index = start.month - 1 + months
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        day = min(start.day, monthrange(year, month)[1])
        return date(year, month, day)
