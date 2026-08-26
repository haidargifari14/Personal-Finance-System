"""Regression tests for Sprint 8.7G Goal V2 Account integration."""

from __future__ import annotations

from datetime import date
import unittest

from services.account_movement_service import AccountMovementService
from services.account_service import AccountService
from services.goal_schema import GOAL_PHYSICAL_HEADERS, is_valid_goal_id
from services.goal_service import GoalService
from services.sheet_service import SheetService


class _FakeSheetService:
    """In-memory repository double shared by Account, Movement, and Goal services."""

    def __init__(self) -> None:
        self.accounts: dict[str, dict[str, object]] = {}
        self.transactions: list[dict[str, object]] = []
        self.movements: dict[str, dict[str, object]] = {}
        self.goals: dict[str, dict[str, object]] = {}

    def append_account(self, account: dict[str, object]) -> None:
        self.accounts[str(account["account_id"])] = dict(account)

    def get_accounts(self) -> list[dict[str, object]]:
        return [{**item, "row_number": index} for index, item in enumerate(self.accounts.values(), 2)]

    def update_account(self, account_id: str, account: dict[str, object]) -> None:
        self.accounts[account_id] = dict(account)

    def delete_account(self, account_id: str) -> None:
        del self.accounts[account_id]

    def append(self, transaction: dict[str, object]) -> None:
        self.transactions.append(dict(transaction))

    def get_transactions(self) -> list[dict[str, object]]:
        return list(self.transactions)

    def append_account_movement(self, movement: dict[str, object]) -> None:
        self.movements[str(movement["movement_id"])] = dict(movement)

    def get_account_movements(self) -> list[dict[str, object]]:
        return [{**item, "row_number": index} for index, item in enumerate(self.movements.values(), 2)]

    def delete_account_movement(self, movement_id: str) -> None:
        del self.movements[movement_id]

    def append_goal(self, goal: dict[str, object]) -> None:
        self.goals[str(goal["goal_id"])] = dict(goal)

    def get_goals(self) -> list[dict[str, object]]:
        return [{**item, "row_number": index} for index, item in enumerate(self.goals.values(), 2)]

    def update_goal(self, goal_id: str, goal: dict[str, object]) -> None:
        self.goals[goal_id] = dict(goal)

    def delete_goal(self, goal_id: str) -> None:
        del self.goals[goal_id]


class _FakeGoalsWorksheet:
    """Minimal worksheet fake for Goal V2 schema creation tests."""

    def __init__(self) -> None:
        self.headers: list[str] = []
        self.update_calls = 0

    def row_values(self, row: int) -> list[str]:
        return list(self.headers)

    def update(self, cell_range: str, values: list[list[str]]) -> None:
        self.headers = list(values[0])
        self.update_calls += 1


class GoalServiceTests(unittest.TestCase):
    """Verify Goal V2 progress is derived solely from linked Account data."""

    def setUp(self) -> None:
        self.sheet = _FakeSheetService()
        self.accounts = AccountService(self.sheet)
        self.movements = AccountMovementService(self.sheet)
        self.goals = GoalService(self.sheet)
        self.laptop = self.accounts.create_account(
            account_name="Laptop", account_location="BCA", initial_balance=3_000_000
        )
        self.reserve = self.accounts.create_account(
            account_name="Reserve", account_location="DANA", initial_balance=1_000_000
        )

    def _create_goal(self, **overrides):
        values = {"account_id": self.laptop.account_id, "target_amount": 10_000_000,
                  "priority": "high", "deadline": date(2026, 12, 31)}
        values.update(overrides)
        return self.goals.create_goal(**values)

    def _summary(self, goal_id: str, today: date = date(2026, 8, 22)) -> dict[str, object]:
        return next(item for item in self.goals.get_goal_summaries(today) if item["goal"].goal_id == goal_id)

    def test_creation_progress_remaining_and_immutable_relationship(self) -> None:
        goal = self._create_goal()
        summary = self._summary(goal.goal_id)

        self.assertTrue(is_valid_goal_id(goal.goal_id))
        self.assertEqual(summary["current_progress"], 3_000_000)
        self.assertEqual(summary["remaining_amount"], 7_000_000)
        self.assertEqual(summary["progress_percent"], 30.0)
        updated = self.goals.update_goal(goal.goal_id, target_amount=12_000_000,
                                         priority="medium", deadline=None)
        self.assertEqual(updated.account_id, self.laptop.account_id)
        self.assertEqual(self.accounts.calculate_current_balance(self.laptop.account_id), 3_000_000)

    def test_transactions_transfers_and_adjustments_change_progress_only_via_account(self) -> None:
        goal = self._create_goal()
        self.sheet.transactions.extend([
            {"account_id": self.laptop.account_id, "type": "expense", "amount": 500_000, "date": "2026-08-01"},
            {"account_id": self.laptop.account_id, "type": "income", "amount": 1_000_000, "date": "2026-08-02"},
        ])
        self.assertEqual(self._summary(goal.goal_id)["current_progress"], 3_500_000)
        self.movements.create_transfer(from_account_id=self.reserve.account_id,
                                       to_account_id=self.laptop.account_id, amount=1_000_000,
                                       movement_date=date(2026, 8, 3))
        self.assertEqual(self._summary(goal.goal_id)["current_progress"], 4_500_000)
        self.movements.create_adjustment(account_id=self.laptop.account_id,
                                         actual_balance=4_000_000,
                                         movement_date=date(2026, 8, 4), reason="cash check")
        self.assertEqual(self._summary(goal.goal_id)["current_progress"], 4_000_000)

    def test_adjustment_is_excluded_from_contribution_pace(self) -> None:
        goal = self._create_goal()
        self.sheet.transactions.extend([
            {"account_id": self.laptop.account_id, "type": "income", "amount": 100_000, "date": "2026-07-01"},
            {"account_id": self.laptop.account_id, "type": "income", "amount": 100_000, "date": "2026-08-01"},
        ])
        self.movements.create_adjustment(account_id=self.laptop.account_id,
                                         actual_balance=9_000_000,
                                         movement_date=date(2026, 8, 2), reason="reconcile")
        pace = self._summary(goal.goal_id)["contribution_pace"]
        self.assertTrue(pace["is_sufficient"])
        self.assertEqual(pace["monthly_amount"], 100_000)

    def test_contribution_pace_includes_transactions_and_transfers_only(self) -> None:
        """Include linked income/transfer-in and subtract expense/transfer-out."""

        goal = self._create_goal()
        self.sheet.transactions.extend([
            {"account_id": self.laptop.account_id, "type": "income", "amount": 200_000, "date": "2026-07-01"},
            {"account_id": self.laptop.account_id, "type": "expense", "amount": 50_000, "date": "2026-07-02"},
            {"account_id": self.laptop.account_id, "type": "income", "amount": 200_000, "date": "2026-08-01"},
            {"account_id": self.laptop.account_id, "type": "expense", "amount": 50_000, "date": "2026-08-02"},
            {"account_id": None, "type": "income", "amount": 999_999, "date": "2026-08-03"},
        ])
        self.movements.create_transfer(
            from_account_id=self.reserve.account_id,
            to_account_id=self.laptop.account_id,
            amount=100_000,
            movement_date=date(2026, 7, 3),
        )
        self.movements.create_transfer(
            from_account_id=self.laptop.account_id,
            to_account_id=self.reserve.account_id,
            amount=100_000,
            movement_date=date(2026, 8, 3),
        )

        pace = self._summary(goal.goal_id)["contribution_pace"]

        self.assertTrue(pace["is_sufficient"])
        self.assertEqual(pace["monthly_amount"], 150_000)

    def test_goal_health_pace_ratio_thresholds(self) -> None:
        """Classify sufficient contribution pace using locked Forecast V2 ratios."""

        sufficient_pace = {"is_sufficient": True, "monthly_amount": 100, "months": 2}
        self.assertEqual(
            GoalService._calculate_health(
                current=0,
                target=1_000,
                deadline=date(2026, 12, 31),
                reference_date=date(2026, 8, 22),
                required_monthly=100,
                pace=sufficient_pace,
            ),
            "On Track",
        )
        self.assertEqual(
            GoalService._calculate_health(
                current=0,
                target=1_000,
                deadline=date(2026, 12, 31),
                reference_date=date(2026, 8, 22),
                required_monthly=100,
                pace={**sufficient_pace, "monthly_amount": 80},
            ),
            "At Risk",
        )
        self.assertEqual(
            GoalService._calculate_health(
                current=0,
                target=1_000,
                deadline=date(2026, 12, 31),
                reference_date=date(2026, 8, 22),
                required_monthly=100,
                pace={**sufficient_pace, "monthly_amount": 79},
            ),
            "Off Track",
        )

    def test_health_achieved_overdue_no_deadline_and_insufficient_history(self) -> None:
        achieved = self._create_goal(target_amount=3_000_000)
        self.assertEqual(self._summary(achieved.goal_id)["health"], "Achieved")
        self.assertEqual(self.goals.list_goals()[0].status, "active")
        self.goals.set_goal_status(achieved.goal_id, "closed")
        overdue = self._create_goal(target_amount=10_000_000, deadline=date(2026, 7, 1))
        self.assertEqual(self._summary(overdue.goal_id)["health"], "Overdue")
        self.goals.set_goal_status(overdue.goal_id, "closed")
        no_deadline = self._create_goal(deadline=None)
        self.assertIsNone(self._summary(no_deadline.goal_id)["required_monthly_contribution"])
        self.assertEqual(self._summary(no_deadline.goal_id)["health"], "No Deadline")
        self.goals.set_goal_status(no_deadline.goal_id, "closed")
        insufficient = self._create_goal(deadline=date(2026, 12, 31))
        self.assertEqual(self._summary(insufficient.goal_id)["health"], "Insufficient Allocation History")

    def test_active_goal_cardinality_close_delete_and_archived_rejection(self) -> None:
        goal = self._create_goal()
        with self.assertRaisesRegex(ValueError, "sudah memiliki Goal aktif"):
            self._create_goal()
        self.goals.set_goal_status(goal.goal_id, "closed")
        replacement = self._create_goal()
        before = self.accounts.calculate_current_balance(self.laptop.account_id)
        self.goals.delete_goal(replacement.goal_id)
        self.assertEqual(self.accounts.calculate_current_balance(self.laptop.account_id), before)

        archived = self.accounts.create_account(account_name="Old", account_location="Cash", initial_balance=0)
        self.accounts.archive_account(archived.account_id)
        with self.assertRaisesRegex(ValueError, "diarsipkan"):
            self.goals.create_goal(account_id=archived.account_id, target_amount=1,
                                   priority="low")

    def test_historical_null_account_transaction_does_not_change_goal_progress(self) -> None:
        goal = self._create_goal()
        self.sheet.transactions.append({"account_id": None, "type": "income", "amount": 900_000, "date": "2026-08-01"})
        self.assertEqual(self._summary(goal.goal_id)["current_progress"], 3_000_000)

    def test_goals_worksheet_initialization_is_idempotent(self) -> None:
        worksheet = _FakeGoalsWorksheet()
        SheetService._ensure_goals_schema(worksheet)
        SheetService._ensure_goals_schema(worksheet)
        self.assertEqual(worksheet.headers, list(GOAL_PHYSICAL_HEADERS))
        self.assertEqual(worksheet.update_calls, 1)


if __name__ == "__main__":
    unittest.main()
