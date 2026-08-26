"""
services/analytics_service.py

Business analytics service for dashboard reporting.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from services.sheet_service import SheetService
from services.category_definitions import EXPENSE_CATEGORIES, INCOME_CATEGORIES


class AnalyticsService:
    """
    Analytics layer for the Personal Finance Dashboard.

    Responsible for:
    - Dashboard KPI
    - Dashboard charts
    - Dashboard tables
    - Business analytics

    Does NOT:
    - Render UI
    - Format currency
    - Access Streamlit
    """

    def __init__(self, sheet_service: SheetService | None = None) -> None:
        """Initialize the transaction-only analytics boundary."""

        self.sheet_service = sheet_service or SheetService()

        # cache dataframe
        self._df: pd.DataFrame | None = None
        self._last_loaded_at: datetime | None = None

    # =====================================================
    # Internal Helper
    # =====================================================

    def _prepare_dataframe(self) -> pd.DataFrame:
        """
        Load transaction dataframe
        and normalize data.
        """

        if self._df is not None:
            return self._df.copy()

        df = self.sheet_service.get_transactions_dataframe()
        get_loaded_at = getattr(self.sheet_service, "get_dataset_loaded_at", None)
        self._last_loaded_at = (
            get_loaded_at("transactions")
            if callable(get_loaded_at)
            else datetime.now()
        )

        if df.empty:
            self._df = df
            return df

        # --------------------------
        # Normalize columns
        # --------------------------

        df["date"] = pd.to_datetime(df["date"])

        df["type"] = (
            df["type"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # Account Movements live in their own worksheet. This defensive filter
        # also prevents malformed/legacy non-economic rows from ever entering
        # Income, Expense, category, trend, or comparison calculations.
        df = df[df["type"].isin({"income", "expense"})].copy()

        df["category"] = (
            df["category"]
            .astype(str)
            .str.strip()
        )

        df["note"] = (
            df["note"]
            .fillna("")
            .astype(str)
        )

        df["amount"] = (
            pd.to_numeric(
                df["amount"]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", "", regex=False),
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        df = df.sort_values(
            by="date",
            ascending=False,
        )

        self._df = df

        return df.copy()

    # =====================================================
    # Filter
    # =====================================================

    @staticmethod
    def _normalize_categories(category: object) -> list[str]:
        """Normalize a single or multi-category filter into category names."""

        if isinstance(category, (list, tuple, set, frozenset)):
            values = category
        else:
            values = (category,)

        return [
            str(value).strip()
            for value in values
            if value not in (None, "", "All") and str(value).strip()
        ]

    def _apply_filters(
        self,
        df: pd.DataFrame,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """
        Apply dashboard filters.
        """

        if df.empty:
            return df

        if start_date is not None:
            start = pd.to_datetime(start_date)
            df = df[df["date"] >= start]

        if end_date is not None:
            end = pd.to_datetime(end_date)
            df = df[df["date"] <= end]

        selected_categories = self._normalize_categories(category)
        if selected_categories:
            df = df[df["category"].isin(selected_categories)]

        if transaction_type not in (None, "", "All"):
            df = df[
                df["type"]
                == transaction_type.lower()
            ]

        return df

    # =====================================================
    # Categories
    # =====================================================

    def get_categories(self) -> list[str]:
        """
        Return all categories.
        """

        df = self._prepare_dataframe()

        categories = sorted(
            {
                *EXPENSE_CATEGORIES,
                *INCOME_CATEGORIES,
                *(
                    df["category"].dropna().unique().tolist()
                    if not df.empty
                    else []
                ),
            }
        )

        return ["All"] + categories

    # =====================================================
    # Dashboard KPI
    # =====================================================

    def get_dashboard_summary(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> dict:

        df = self._prepare_dataframe()

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        if df.empty:

            return {
                "income": 0,
                "expense": 0,
                "saving": 0,
                "net_cashflow": 0,
                "saving_rate": 0,
                "transaction_count": 0,
                "average_expense": 0,
                "average_income": 0,
                "largest_expense": 0,
                "largest_income": 0,
            }

        income_transactions = df[df["type"] == "income"]
        expense_transactions = df[df["type"] == "expense"]

        income = income_transactions["amount"].sum()
        expense = expense_transactions["amount"].sum()

        saving = income - expense

        saving_rate = (
            saving / income * 100
            if income > 0
            else 0
        )
        average_expense = (
            int(expense_transactions["amount"].mean())
            if not expense_transactions.empty
            else 0
        )
        average_income = (
            int(income_transactions["amount"].mean())
            if not income_transactions.empty
            else 0
        )
        largest_expense = (
            int(expense_transactions["amount"].max())
            if not expense_transactions.empty
            else 0
        )
        largest_income = (
            int(income_transactions["amount"].max())
            if not income_transactions.empty
            else 0
        )

        return {
            "income": int(income),
            "expense": int(expense),
            "saving": int(saving),
            "net_cashflow": int(saving),
            "saving_rate": round(saving_rate, 2),
            "transaction_count": len(df),
            "average_expense": average_expense,
            "average_income": average_income,
            "largest_expense": largest_expense,
            "largest_income": largest_income,
        }

    # =====================================================
    # Transactions
    # =====================================================

    def get_recent_transactions(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
        limit: int = 10,
    ) -> pd.DataFrame:
        """
        Return most recent transactions.
        """

        df = self._prepare_dataframe()

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        if df.empty:
            return df

        return df.head(limit).copy()

    def get_transactions(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
        search: str | None = None,
        minimum_amount: int | float | None = None,
        maximum_amount: int | float | None = None,
        sort_by: str = "Date",
        sort_order: str = "Descending",
    ) -> pd.DataFrame:
        """Return transactions filtered and sorted for the Transactions page."""

        df = self._prepare_dataframe()
        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if df.empty:
            return df

        if minimum_amount is not None:
            if minimum_amount < 0:
                raise ValueError("Minimum amount tidak boleh bernilai negatif.")
            df = df[df["amount"] >= minimum_amount]

        if maximum_amount is not None:
            if maximum_amount < 0:
                raise ValueError("Maximum amount tidak boleh bernilai negatif.")
            df = df[df["amount"] <= maximum_amount]

        if (
            minimum_amount is not None
            and maximum_amount is not None
            and minimum_amount > maximum_amount
        ):
            raise ValueError(
                "Minimum amount tidak boleh lebih besar dari maximum amount."
            )

        search_term = (search or "").strip()
        if search_term:
            matches_category = df["category"].str.contains(
                search_term,
                case=False,
                regex=False,
                na=False,
            )
            matches_note = df["note"].str.contains(
                search_term,
                case=False,
                regex=False,
                na=False,
            )
            df = df[matches_category | matches_note]

        sort_column = self._get_transaction_sort_column(sort_by)
        ascending = self._get_transaction_sort_order(sort_order)
        return df.sort_values(
            by=sort_column,
            ascending=ascending,
            kind="stable",
        ).reset_index(drop=True)

    def get_transaction_summary(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
        search: str | None = None,
        minimum_amount: int | float | None = None,
        maximum_amount: int | float | None = None,
        sort_by: str = "Date",
        sort_order: str = "Descending",
    ) -> dict[str, int | datetime | None]:
        """Return Transactions counts and the latest successful sheet-read time."""

        global_filtered = self._apply_filters(
            self._prepare_dataframe(),
            start_date=start_date,
            end_date=end_date,
        )
        displayed_transactions = self.get_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
            search=search,
            minimum_amount=minimum_amount,
            maximum_amount=maximum_amount,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        displayed_count = len(displayed_transactions)
        return {
            "showing": displayed_count,
            "total": displayed_count,
            "filtered_from": len(global_filtered),
            "last_updated": getattr(self, "_last_loaded_at", None),
        }

    @staticmethod
    def _get_transaction_sort_column(sort_by: str) -> str:
        """Map a Transactions sort label to a supported dataframe column."""

        sort_columns = {
            "date": "date",
            "amount": "amount",
            "category": "category",
        }
        sort_column = sort_columns.get(sort_by.strip().lower())
        if sort_column is None:
            raise ValueError("Unsupported transaction sort field.")

        return sort_column

    @staticmethod
    def _get_transaction_sort_order(sort_order: str) -> bool:
        """Return whether the requested Transactions sort order is ascending."""

        normalized_order = sort_order.strip().lower()
        if normalized_order == "ascending":
            return True
        if normalized_order == "descending":
            return False
        raise ValueError("Unsupported transaction sort order.")

    # =====================================================
    # Charts
    # =====================================================

    def get_income_vs_expense(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """
        Return income vs expense summary
        for bar chart.
        """

        df = self._prepare_dataframe()

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        if df.empty:
            return pd.DataFrame(
                {
                    "type": ["Income", "Expense"],
                    "amount": [0, 0],
                }
            )

        income = df.loc[
            df["type"] == "income",
            "amount",
        ].sum()

        expense = df.loc[
            df["type"] == "expense",
            "amount",
        ].sum()

        return pd.DataFrame(
            {
                "type": [
                    "Income",
                    "Expense",
                ],
                "amount": [
                    int(income),
                    int(expense),
                ],
            }
        )

    def get_expense_by_category(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """Return expense totals grouped by category for a pie chart."""

        df = self._prepare_dataframe()
        if df.empty:
            return pd.DataFrame(columns=["category", "amount"])

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        expenses = df[df["type"] == "expense"]
        if expenses.empty:
            return pd.DataFrame(columns=["category", "amount"])

        return (
            expenses.groupby("category", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
        )

    def get_top_spending_categories(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
        limit: int = 3,
    ) -> pd.DataFrame:
        """Return the highest expense categories with their total percentages."""

        expense_by_category = self.get_expense_by_category(
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if expense_by_category.empty:
            return pd.DataFrame(
                columns=["rank", "category", "amount", "percentage"]
            )

        total_expense = expense_by_category["amount"].sum()
        top_categories = expense_by_category.head(min(max(limit, 1), 3)).copy()
        top_categories.insert(0, "rank", range(1, len(top_categories) + 1))
        top_categories["percentage"] = (
            top_categories["amount"] / total_expense * 100
        ).round(2)

        return top_categories

    def get_category_drilldown(
        self,
        selected_category: str,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
        limit: int = 10,
    ) -> dict[str, object]:
        """Return summary, monthly trend, and transactions for one expense category."""

        df = self._prepare_dataframe()
        filtered_transactions = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if filtered_transactions.empty:
            return {
                "summary": self._empty_category_summary(selected_category),
                "monthly_trend": pd.DataFrame(columns=["month", "amount"]),
                "transactions": filtered_transactions,
            }

        expenses = filtered_transactions[
            filtered_transactions["type"] == "expense"
        ]
        category_transactions = expenses[
            expenses["category"] == selected_category
        ].copy()

        if category_transactions.empty:
            return {
                "summary": self._empty_category_summary(selected_category),
                "monthly_trend": pd.DataFrame(columns=["month", "amount"]),
                "transactions": category_transactions,
            }

        total_expense = expenses["amount"].sum()
        monthly_trend = (
            category_transactions.assign(
                month=category_transactions["date"].dt.to_period("M").dt.to_timestamp()
            )
            .groupby("month", as_index=False)["amount"]
            .sum()
            .sort_values("month")
        )
        transaction_limit = min(max(limit, 1), 10)

        return {
            "summary": {
                "category": selected_category,
                "total_expense": int(category_transactions["amount"].sum()),
                "average_expense": int(category_transactions["amount"].mean()),
                "highest_expense": int(category_transactions["amount"].max()),
                "transaction_count": len(category_transactions),
                "contribution": round(
                    category_transactions["amount"].sum() / total_expense * 100
                    if total_expense > 0
                    else 0,
                    2,
                ),
            },
            "monthly_trend": monthly_trend,
            "transactions": category_transactions.head(transaction_limit),
        }

    @staticmethod
    def _empty_category_summary(selected_category: str) -> dict[str, int | float | str]:
        """Return an empty drilldown summary for the selected category."""

        return {
            "category": selected_category,
            "total_expense": 0,
            "average_expense": 0,
            "highest_expense": 0,
            "transaction_count": 0,
            "contribution": 0,
        }

    def get_period_comparison(
        self,
        *,
        start_date,
        end_date,
        category=None,
        transaction_type=None,
    ) -> dict[str, object]:
        """Compare filtered financial data with the immediately preceding period."""

        current_start = pd.to_datetime(start_date).normalize()
        current_end = pd.to_datetime(end_date).normalize()
        if current_start > current_end:
            raise ValueError("The comparison start date must not exceed the end date.")

        period_length = (current_end - current_start).days + 1
        previous_end = current_start - pd.Timedelta(days=1)
        previous_start = previous_end - pd.Timedelta(days=period_length - 1)

        current_transactions = self._get_period_transactions(
            current_start,
            current_end,
            category=category,
            transaction_type=transaction_type,
        )
        previous_transactions = self._get_period_transactions(
            previous_start,
            previous_end,
            category=category,
            transaction_type=transaction_type,
        )
        current_metrics = self._get_period_financial_metrics(current_transactions)
        previous_metrics = self._get_period_financial_metrics(previous_transactions)

        return {
            "current_period": {"start_date": current_start, "end_date": current_end},
            "previous_period": {
                "start_date": previous_start,
                "end_date": previous_end,
            },
            "financial_comparison": {
                metric: self._build_comparison_item(
                    current_metrics[metric],
                    previous_metrics[metric],
                )
                for metric in ("income", "expense", "saving", "saving_rate")
            },
            "category_comparison": self._build_category_comparison(
                current_transactions,
                previous_transactions,
            ),
        }

    def _get_period_transactions(
        self,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        *,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """Return transactions for a comparison period using the active filters."""

        df = self._prepare_dataframe()
        return self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

    @staticmethod
    def _get_period_financial_metrics(df: pd.DataFrame) -> dict[str, float | int]:
        """Calculate the core metrics for a single comparison period."""

        income = df.loc[df["type"] == "income", "amount"].sum()
        expense = df.loc[df["type"] == "expense", "amount"].sum()
        saving = income - expense
        saving_rate = saving / income * 100 if income > 0 else 0

        return {
            "income": int(income),
            "expense": int(expense),
            "saving": int(saving),
            "saving_rate": round(saving_rate, 2),
        }

    @classmethod
    def _build_comparison_item(
        cls,
        current_value: float | int,
        previous_value: float | int,
    ) -> dict[str, float | int | str | None]:
        """Build one current-versus-previous comparison item."""

        difference = current_value - previous_value
        return {
            "current": current_value,
            "previous": previous_value,
            "difference": difference,
            "percentage_change": cls._calculate_percentage_change(
                current_value,
                previous_value,
            ),
            "indicator": cls._get_change_indicator(difference),
        }

    @staticmethod
    def _calculate_percentage_change(
        current_value: float | int,
        previous_value: float | int,
    ) -> float | None:
        """Calculate a safe percentage change for comparison output."""

        if previous_value == 0:
            return 0.0 if current_value == 0 else None

        return round(
            (current_value - previous_value) / abs(previous_value) * 100,
            2,
        )

    @staticmethod
    def _get_change_indicator(difference: float | int) -> str:
        """Return the neutral directional indicator for a comparison value."""

        if difference > 0:
            return "increase"
        if difference < 0:
            return "decrease"
        return "no_change"

    @classmethod
    def _build_category_comparison(
        cls,
        current_transactions: pd.DataFrame,
        previous_transactions: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compare expense totals by category for two filtered periods."""

        current_expenses = current_transactions[
            current_transactions["type"] == "expense"
        ]
        previous_expenses = previous_transactions[
            previous_transactions["type"] == "expense"
        ]
        current_totals = (
            current_expenses.groupby("category", as_index=False)["amount"]
            .sum()
            .rename(columns={"amount": "current_expense"})
        )
        previous_totals = (
            previous_expenses.groupby("category", as_index=False)["amount"]
            .sum()
            .rename(columns={"amount": "previous_expense"})
        )
        comparison = pd.merge(
            current_totals,
            previous_totals,
            on="category",
            how="outer",
        ).fillna(0)
        if comparison.empty:
            return pd.DataFrame(
                columns=[
                    "category",
                    "current_expense",
                    "previous_expense",
                    "difference",
                    "percentage_change",
                    "indicator",
                ]
            )

        comparison["current_expense"] = comparison["current_expense"].astype(int)
        comparison["previous_expense"] = comparison["previous_expense"].astype(int)
        comparison["difference"] = (
            comparison["current_expense"] - comparison["previous_expense"]
        )
        comparison["percentage_change"] = [
            cls._calculate_percentage_change(current, previous)
            for current, previous in zip(
                comparison["current_expense"],
                comparison["previous_expense"],
            )
        ]
        comparison["indicator"] = comparison["difference"].apply(
            cls._get_change_indicator
        )

        return comparison.sort_values(
            ["current_expense", "category"],
            ascending=[False, True],
        ).reset_index(drop=True)

    def get_cashflow_trend(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """Return daily income and expense totals for a cashflow trend chart."""

        df = self._prepare_dataframe()
        if df.empty:
            return pd.DataFrame(columns=["date", "income", "expense"])

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if df.empty:
            return pd.DataFrame(columns=["date", "income", "expense"])

        daily_totals = (
            df.groupby(["date", "type"], as_index=False)["amount"]
            .sum()
            .pivot(index="date", columns="type", values="amount")
            .reindex(columns=["income", "expense"], fill_value=0)
            .fillna(0)
            .reset_index()
            .sort_values("date")
        )
        daily_totals["income"] = daily_totals["income"].astype(int)
        daily_totals["expense"] = daily_totals["expense"].astype(int)

        return daily_totals

    def get_monthly_trend(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> pd.DataFrame:
        """Return monthly income and expense totals for a grouped bar chart."""

        df = self._prepare_dataframe()
        if df.empty:
            return pd.DataFrame(columns=["month", "income", "expense"])

        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if df.empty:
            return pd.DataFrame(columns=["month", "income", "expense"])

        monthly_totals = (
            df.assign(month=df["date"].dt.to_period("M").dt.to_timestamp())
            .groupby(["month", "type"], as_index=False)["amount"]
            .sum()
            .pivot(index="month", columns="type", values="amount")
            .reindex(columns=["income", "expense"], fill_value=0)
            .fillna(0)
            .reset_index()
            .sort_values("month")
        )
        monthly_totals["income"] = monthly_totals["income"].astype(int)
        monthly_totals["expense"] = monthly_totals["expense"].astype(int)

        return monthly_totals

    # =====================================================
    # Financial Statistics
    # =====================================================

    def get_financial_statistics(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> dict[str, int | float | None]:
        """Return filtered transaction statistics for the Analytics page."""

        df = self._prepare_dataframe()
        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if df.empty:
            return self._empty_financial_statistics()

        income_transactions = df[df["type"] == "income"]
        expense_transactions = df[df["type"] == "expense"]
        income = int(income_transactions["amount"].sum())
        expense = int(expense_transactions["amount"].sum())
        transaction_count = len(df)

        return {
            "average_income": self._get_average_amount(income_transactions),
            "largest_income": self._get_largest_amount(income_transactions),
            "average_expense": self._get_average_amount(expense_transactions),
            "largest_expense": self._get_largest_amount(expense_transactions),
            "average_saving": int((income - expense) / transaction_count),
            "expense_income_ratio": round(expense / income * 100, 2)
            if income > 0
            else None,
            "average_transaction_value": int(
                df["amount"].sum() / transaction_count
            ),
            "transaction_count": transaction_count,
        }

    @staticmethod
    def _empty_financial_statistics() -> dict[str, int | float | None]:
        """Return empty Financial Statistics values for a filtered empty state."""

        return {
            "average_income": None,
            "largest_income": None,
            "average_expense": None,
            "largest_expense": None,
            "average_saving": None,
            "expense_income_ratio": None,
            "average_transaction_value": None,
            "transaction_count": 0,
        }

    @staticmethod
    def _get_average_amount(transactions: pd.DataFrame) -> int | None:
        """Return the average transaction amount when transactions exist."""

        if transactions.empty:
            return None

        return int(transactions["amount"].mean())

    @staticmethod
    def _get_largest_amount(transactions: pd.DataFrame) -> int | None:
        """Return the largest transaction amount when transactions exist."""

        if transactions.empty:
            return None

        return int(transactions["amount"].max())

    # =====================================================
    # Financial Summary
    # =====================================================

    def get_financial_summary(
        self,
        *,
        start_date=None,
        end_date=None,
        category=None,
        transaction_type=None,
    ) -> dict:
        """Return rule-based financial insights for the dashboard."""

        df = self._prepare_dataframe()
        df = self._apply_filters(
            df,
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        summary = self.get_dashboard_summary(
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )
        if df.empty:
            return {
                "saving_rate": 0,
                "saving_rate_status": None,
                "top_expense_category": None,
                "transaction_count": 0,
                "highest_expense": None,
                "highest_income": None,
            }

        expense_by_category = self.get_expense_by_category(
            start_date=start_date,
            end_date=end_date,
            category=category,
            transaction_type=transaction_type,
        )

        return {
            "saving_rate": summary["saving_rate"],
            "saving_rate_status": self._get_saving_rate_status(
                summary["saving_rate"]
            ),
            "top_expense_category": self._get_top_expense_category(
                expense_by_category
            ),
            "transaction_count": summary["transaction_count"],
            "highest_expense": self._get_highest_transaction(df, "expense"),
            "highest_income": self._get_highest_transaction(df, "income"),
        }

    @staticmethod
    def _get_saving_rate_status(saving_rate: float) -> str:
        """Classify a saving rate using the dashboard summary rules."""

        if saving_rate > 50:
            return "Excellent"
        if saving_rate >= 30:
            return "Good"
        if saving_rate >= 10:
            return "Fair"
        return "Poor"

    @staticmethod
    def _get_top_expense_category(
        expense_by_category: pd.DataFrame,
    ) -> dict | None:
        """Return the largest expense category, when one is available."""

        if expense_by_category.empty:
            return None

        top_category = expense_by_category.iloc[0]
        return {
            "category": str(top_category["category"]),
            "amount": int(top_category["amount"]),
        }

    @staticmethod
    def _get_highest_transaction(
        df: pd.DataFrame,
        transaction_type: str,
    ) -> dict | None:
        """Return the largest transaction for the requested transaction type."""

        transactions = df[df["type"] == transaction_type]
        if transactions.empty:
            return None

        highest_transaction = transactions.loc[transactions["amount"].idxmax()]
        return {
            "amount": int(highest_transaction["amount"]),
            "category": str(highest_transaction["category"]),
            "note": str(highest_transaction["note"]),
        }

    # =====================================================
    # Cache
    # =====================================================

    def get_last_loaded_at(self) -> datetime | None:
        """Return the source timestamp of the current transaction snapshot."""

        return self._last_loaded_at

    def clear_cache(self) -> None:
        """
        Clear cached dataframe.

        Useful after new transaction
        is added from Telegram Bot.
        """

        self._df = None
        self._last_loaded_at = None
        invalidate = getattr(self.sheet_service, "invalidate_read_cache", None)
        if callable(invalidate):
            invalidate("transactions")
