"""Regression tests for centralized Google Sheets read caching."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch
from uuid import uuid4

from services.account_schema import ACCOUNT_HEADERS
from services.account_service import AccountService
from services.analytics_service import AnalyticsService
from services.forecast_service import ForecastService
from services.goal_schema import GOAL_HEADERS
from services.goal_service import GoalService
from services.recommendation_service import RecommendationService
from services.sheet_service import SheetService, SheetsReadError
from services.transaction_schema import SHEET_HEADERS


class _FakeWorksheet:
    """Minimal remote worksheet double with an observable read count."""

    def __init__(self, records: list[dict[str, object]] | None = None) -> None:
        self.records = records or []
        self.read_calls = 0
        self.appended_rows: list[list[object]] = []
        self.error: Exception | None = None
        self.write_error: Exception | None = None

    def get_all_records(self, default_blank=None) -> list[dict[str, object]]:
        """Return configured records or raise the configured transient error."""

        del default_blank
        self.read_calls += 1
        if self.error:
            raise self.error
        return [dict(record) for record in self.records]

    def append_row(self, row: list[object]) -> None:
        """Record one successful mutation without simulating worksheet mapping."""

        if self.write_error:
            raise self.write_error
        self.appended_rows.append(list(row))


class SheetReadCacheTests(unittest.TestCase):
    """Verify bounded reads, invalidation, retries, and stale fallback."""

    def setUp(self) -> None:
        SheetService.reset_read_cache_for_testing()
        self.service = object.__new__(SheetService)
        self.transactions = _FakeWorksheet([
            {
                "Tanggal": "2026-08-24",
                "Jenis": "expense",
                "Kategori": "Makan",
                "Nominal": 10_000,
                "Catatan": "Test",
                "Transaction ID": str(uuid4()),
                "Account ID": "",
            }
        ])
        self.service._worksheet = self.transactions

    def tearDown(self) -> None:
        SheetService.CACHE_TTL_SECONDS = 45
        SheetService.reset_read_cache_for_testing()

    def test_repeated_dataset_read_uses_one_remote_read_inside_ttl(self) -> None:
        """A repeated transaction read must reuse the central source snapshot."""

        first = self.service.get_transactions()
        second = self.service.get_transactions()

        self.assertEqual(first, second)
        self.assertEqual(self.transactions.read_calls, 1)
        metrics = SheetService.get_read_cache_status()["transactions"]
        self.assertEqual(metrics["remote_reads"], 1)
        self.assertEqual(metrics["cache_hits"], 1)

    def test_explicit_invalidation_forces_the_next_remote_read(self) -> None:
        """Refresh semantics must discard only the requested dataset snapshot."""

        self.service.get_transactions()
        SheetService.invalidate_read_cache("transactions")
        self.service.get_transactions()

        self.assertEqual(self.transactions.read_calls, 2)

    def test_transaction_mutation_invalidates_its_snapshot(self) -> None:
        """A successful transaction append makes the next read fetch fresh data."""

        self.service.get_transactions()
        self.service.append(
            {
                "date": "2026-08-24",
                "type": "expense",
                "category": "Makan",
                "amount": 20_000,
                "note": "Mutation",
                "transaction_id": str(uuid4()),
                "account_id": None,
            }
        )
        self.service.get_transactions()

        self.assertEqual(self.transactions.read_calls, 2)
        self.assertEqual(len(self.transactions.appended_rows), 1)

    def test_movement_and_goal_mutations_invalidate_only_their_datasets(self) -> None:
        """Movement and Goal writes must refresh their dependent raw snapshots."""

        movements = _FakeWorksheet()
        goals = _FakeWorksheet()
        self.service._account_movements_worksheet = movements
        self.service._goals_worksheet = goals

        self.service._read_cached_records("account_movements", movements.get_all_records)
        self.service._read_cached_records("goals", goals.get_all_records)
        self.service.append_account_movement(
            {
                "movement_id": str(uuid4()),
                "date": "2026-08-24",
                "movement_type": "adjustment",
                "from_account_id": None,
                "to_account_id": None,
                "account_id": str(uuid4()),
                "amount": 1_000,
                "note": "Test",
                "created_at": "2026-08-24T10:00:00",
                "updated_at": "2026-08-24T10:00:00",
            }
        )
        self.service.append_goal(
            {
                "goal_id": str(uuid4()),
                "account_id": str(uuid4()),
                "target_amount": 100_000,
                "deadline": None,
                "priority": "medium",
                "status": "active",
                "created_at": "2026-08-24T10:00:00",
                "updated_at": "2026-08-24T10:00:00",
            }
        )

        self.service._read_cached_records("account_movements", movements.get_all_records)
        self.service._read_cached_records("goals", goals.get_all_records)

        self.assertEqual(movements.read_calls, 2)
        self.assertEqual(goals.read_calls, 2)
        self.assertEqual(self.transactions.read_calls, 0)

    def test_account_mutation_invalidates_the_account_snapshot(self) -> None:
        """Account writes must not leave AccountService with an old record list."""

        accounts = _FakeWorksheet()
        self.service._accounts_worksheet = accounts
        self.service._read_cached_records("accounts", accounts.get_all_records)
        self.service.append_account(
            {
                "account_id": str(uuid4()),
                "account_name": "Daily Fund",
                "account_location": "DANA",
                "initial_balance": 100_000,
                "tracking_start_date": "2026-08-24",
                "status": "active",
                "created_at": "2026-08-24T10:00:00",
                "updated_at": "2026-08-24T10:00:00",
            }
        )
        self.service._read_cached_records("accounts", accounts.get_all_records)

        self.assertEqual(accounts.read_calls, 2)
        self.assertEqual(self.transactions.read_calls, 0)

    def test_failed_write_keeps_the_last_confirmed_snapshot(self) -> None:
        """A failed mutation must not invalidate data as if it had succeeded."""

        self.service.get_transactions()
        self.transactions.write_error = OSError("Temporary write failure")

        with self.assertRaises(OSError):
            self.service.append(
                {
                    "date": "2026-08-24",
                    "type": "expense",
                    "category": "Makan",
                    "amount": 20_000,
                    "note": "Failed mutation",
                    "transaction_id": str(uuid4()),
                    "account_id": None,
                }
            )

        self.service.get_transactions()
        self.assertEqual(self.transactions.read_calls, 1)

    def test_transient_429_retries_only_the_configured_number_of_times(self) -> None:
        """Quota failures must stop after bounded retry attempts."""

        self.transactions.error = RuntimeError("[429] Quota exceeded")
        with patch("services.sheet_service.time.sleep") as sleep:
            with self.assertRaises(SheetsReadError):
                self.service.get_transactions()

        self.assertEqual(self.transactions.read_calls, SheetService.MAX_READ_ATTEMPTS)
        self.assertEqual(sleep.call_count, SheetService.MAX_READ_ATTEMPTS - 1)

    def test_stale_snapshot_is_returned_after_a_temporary_read_failure(self) -> None:
        """An expired last-known snapshot remains usable with an explicit warning."""

        first = self.service.get_transactions()
        SheetService.CACHE_TTL_SECONDS = 0
        self.transactions.error = RuntimeError("[429] Quota exceeded")

        with patch("services.sheet_service.time.sleep"):
            fallback = self.service.get_transactions()

        self.assertEqual(fallback, first)
        status = SheetService.get_read_cache_status()["transactions"]
        self.assertTrue(status["is_stale"])
        self.assertIn("temporarily unavailable", str(status["warning"]))

    def test_service_construction_is_not_required_for_snapshot_reuse(self) -> None:
        """Separate repository instances share one process-level dataset cache."""

        other_service = object.__new__(SheetService)
        other_service._worksheet = self.transactions

        self.service.get_transactions()
        other_service.get_transactions()

        self.assertEqual(self.transactions.read_calls, 1)

    def test_forecast_reuses_four_snapshots_without_changing_results(self) -> None:
        """A complex Forecast cycle reads each worksheet once inside the TTL."""

        uncached_result, uncached_reads = self._run_forecast_cycle(ttl_seconds=0)
        cached_result, cached_reads = self._run_forecast_cycle(ttl_seconds=45)

        self.assertEqual(cached_result, uncached_result)
        self.assertEqual(
            cached_reads,
            {
                "transactions": 1,
                "accounts": 1,
                "account_movements": 1,
                "goals": 1,
            },
        )
        self.assertGreater(uncached_reads["transactions"], 1)
        self.assertGreater(uncached_reads["accounts"], 1)
        self.assertGreater(uncached_reads["account_movements"], 1)

    def _run_forecast_cycle(
        self,
        *,
        ttl_seconds: int,
    ) -> tuple[tuple[object, ...], dict[str, int]]:
        """Measure one service-equivalent Forecast render without live Sheets."""

        SheetService.reset_read_cache_for_testing()
        SheetService.CACHE_TTL_SECONDS = ttl_seconds
        account_id = "11111111-1111-4111-8111-111111111111"
        sheet = object.__new__(SheetService)
        sheet._worksheet = _FakeWorksheet(
            [
                {
                    SHEET_HEADERS["date"]: "2026-08-20",
                    SHEET_HEADERS["type"]: "income",
                    SHEET_HEADERS["category"]: "Gaji",
                    SHEET_HEADERS["amount"]: 1_000_000,
                    SHEET_HEADERS["note"]: "Income",
                    SHEET_HEADERS["transaction_id"]: "22222222-2222-4222-8222-222222222222",
                    SHEET_HEADERS["account_id"]: account_id,
                },
                {
                    SHEET_HEADERS["date"]: "2026-08-21",
                    SHEET_HEADERS["type"]: "expense",
                    SHEET_HEADERS["category"]: "Makan",
                    SHEET_HEADERS["amount"]: 100_000,
                    SHEET_HEADERS["note"]: "Expense",
                    SHEET_HEADERS["transaction_id"]: "33333333-3333-4333-8333-333333333333",
                    SHEET_HEADERS["account_id"]: account_id,
                },
            ]
        )
        sheet._accounts_worksheet = _FakeWorksheet(
            [
                {
                    ACCOUNT_HEADERS["account_id"]: account_id,
                    ACCOUNT_HEADERS["account_name"]: "Daily Fund",
                    ACCOUNT_HEADERS["account_location"]: "DANA",
                    ACCOUNT_HEADERS["initial_balance"]: 100_000,
                    ACCOUNT_HEADERS["tracking_start_date"]: "2026-08-01",
                    ACCOUNT_HEADERS["status"]: "active",
                    ACCOUNT_HEADERS["created_at"]: "2026-08-01T10:00:00",
                    ACCOUNT_HEADERS["updated_at"]: "2026-08-01T10:00:00",
                }
            ]
        )
        sheet._account_movements_worksheet = _FakeWorksheet()
        sheet._goals_worksheet = _FakeWorksheet(
            [
                {
                    GOAL_HEADERS["goal_id"]: "44444444-4444-4444-8444-444444444444",
                    GOAL_HEADERS["account_id"]: account_id,
                    GOAL_HEADERS["target_amount"]: 2_000_000,
                    GOAL_HEADERS["deadline"]: "2026-12-31",
                    GOAL_HEADERS["priority"]: "high",
                    GOAL_HEADERS["status"]: "active",
                    GOAL_HEADERS["created_at"]: "2026-08-01T10:00:00",
                    GOAL_HEADERS["updated_at"]: "2026-08-01T10:00:00",
                }
            ]
        )
        analytics = AnalyticsService(sheet)
        forecast = ForecastService(
            analytics,
            AccountService(sheet),
            GoalService(sheet),
        )
        reference_date = date(2026, 8, 24)
        expense_forecast = forecast.get_expense_forecast(reference_date)
        outlook = forecast.get_financial_outlook(
            [],
            reference_date,
            expense_forecast,
        )
        goal_forecast = forecast.get_goal_forecast(reference_date)
        spending_limit_status = forecast.get_monthly_spending_limit_status(
            monthly_spending_limit=1_500_000,
            expense_forecast=expense_forecast,
            financial_outlook=outlook,
        )
        recommendation = RecommendationService().get_recommendations(
            financial_outlook=outlook,
            expense_forecast=expense_forecast,
            goal_forecast=goal_forecast,
            saving_candidates={"Makan": True},
            spending_limit_status=spending_limit_status,
        )
        reads = {
            "transactions": sheet._worksheet.read_calls,
            "accounts": sheet._accounts_worksheet.read_calls,
            "account_movements": sheet._account_movements_worksheet.read_calls,
            "goals": sheet._goals_worksheet.read_calls,
        }
        return (expense_forecast, outlook, goal_forecast, recommendation), reads


if __name__ == "__main__":
    unittest.main()
