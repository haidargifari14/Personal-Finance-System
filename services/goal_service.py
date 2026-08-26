"""Goal V2 domain logic linked to Account allocations."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Mapping

from models.account import Account
from models.goal import Goal
from services.account_service import AccountService
from services.goal_schema import GOAL_PRIORITIES, new_goal_id
from services.sheet_service import SheetService


class GoalService:
    """Manage Goal V2 configurations and derived Account-based Goal metrics."""

    MIN_HISTORY_MONTHS = 2

    def __init__(self, sheet_service: SheetService | None = None) -> None:
        """Initialize shared Account and persistence dependencies."""

        self._sheet_service = sheet_service
        self._account_service = AccountService(self._get_sheet_service())

    def create_goal(self, *, account_id: str, target_amount: int | float | str,
                    priority: str, deadline: date | None = None) -> Goal:
        """Create one Active Goal for an eligible active Account."""

        account = self._account_service.validate_active_account(account_id)
        if self._has_active_goal(account.account_id):
            raise ValueError("Akun ini sudah memiliki Goal aktif.")
        record = self._new_goal_record(
            account_id=account.account_id,
            target_amount=self._validate_target_amount(target_amount),
            priority=self._validate_priority(priority), deadline=deadline, status="active",
        )
        self._get_sheet_service().append_goal(record)
        return Goal.from_record(record)

    def list_goals(self) -> list[Goal]:
        """Return all Goal V2 records, including closed history."""

        return [Goal.from_record(record) for record in self._get_sheet_service().get_goals()]

    def get_eligible_accounts(self) -> list[Account]:
        """Return active Accounts without an active Goal."""

        return [account for account in self._account_service.list_active_accounts()
                if not self._has_active_goal(account.account_id)]

    def update_goal(self, goal_id: str, *, target_amount: int | float | str,
                    priority: str, deadline: date | None) -> Goal:
        """Edit mutable Goal metadata while preserving Account and Goal identity."""

        existing = self._get_goal_record(goal_id)
        updated = {
            **existing, "target_amount": self._validate_target_amount(target_amount),
            "priority": self._validate_priority(priority),
            "deadline": deadline.isoformat() if deadline else None,
            "updated_at": self._now_text(),
        }
        self._get_sheet_service().update_goal(goal_id, updated)
        return Goal.from_record(updated)

    def set_goal_status(self, goal_id: str, status: str) -> Goal:
        """Pause, resume, or close a Goal without changing financial data."""

        normalized_status = str(status).strip().lower()
        if normalized_status not in {"active", "paused", "closed"}:
            raise ValueError("Status Goal tidak valid.")
        existing = self._get_goal_record(goal_id)
        if normalized_status == "active" and self._has_active_goal(
            str(existing["account_id"]), exclude_goal_id=goal_id,
        ):
            raise ValueError("Akun ini sudah memiliki Goal aktif.")
        updated = {**existing, "status": normalized_status, "updated_at": self._now_text()}
        self._get_sheet_service().update_goal(goal_id, updated)
        return Goal.from_record(updated)

    def delete_goal(self, goal_id: str) -> None:
        """Delete only a Goal configuration; finance data remains intact."""

        self._get_goal_record(goal_id)
        self._get_sheet_service().delete_goal(goal_id)

    def get_goal_summaries(self, today: date | None = None) -> list[dict[str, object]]:
        """Return Goals together with service-derived progress and health metrics."""

        reference_date = today or date.today()
        summaries: list[dict[str, object]] = []
        for goal in self.list_goals():
            account = self._find_account(goal.account_id)
            if account is None:
                summaries.append(self._orphaned_summary(goal))
                continue
            current = self._account_service.calculate_current_balance(goal.account_id)
            remaining = max(goal.target_amount - current, 0)
            progress_percent = (current / goal.target_amount) * 100
            deadline = self._parse_deadline(goal.deadline)
            required_monthly = self._required_monthly_contribution(remaining, deadline, reference_date)
            pace = self._contribution_pace(goal.account_id, reference_date)
            health = self._calculate_health(
                current=current, target=goal.target_amount, deadline=deadline,
                reference_date=reference_date, required_monthly=required_monthly, pace=pace,
            )
            summaries.append({
                "goal": goal, "account": account, "current_progress": current,
                "remaining_amount": remaining, "progress_percent": progress_percent,
                "required_monthly_contribution": required_monthly,
                "contribution_pace": pace, "health": health,
            })
        return summaries

    def _new_goal_record(self, *, account_id: str, target_amount: int,
                         priority: str, deadline: date | None, status: str) -> dict[str, object]:
        """Build an immutable Goal record ready for persistence."""

        now = self._now_text()
        return {
            "goal_id": new_goal_id(), "account_id": account_id,
            "target_amount": target_amount,
            "deadline": deadline.isoformat() if deadline else None,
            "priority": priority, "status": status,
            "created_at": now, "updated_at": now,
        }

    def _has_active_goal(self, account_id: str, exclude_goal_id: str | None = None) -> bool:
        """Return whether an Account owns another active Goal."""

        return any(goal.account_id == account_id and goal.status == "active"
                   and goal.goal_id != exclude_goal_id for goal in self.list_goals())

    def _get_goal_record(self, goal_id: str) -> dict[str, Any]:
        """Load one Goal record by immutable identity."""

        for record in self._get_sheet_service().get_goals():
            if record["goal_id"] == str(goal_id).strip():
                return {key: value for key, value in record.items() if key != "row_number"}
        raise ValueError("Goal tidak ditemukan.")

    def _find_account(self, account_id: str) -> Account | None:
        """Return a linked Account or retain orphaned historical Goals safely."""

        try:
            return self._account_service.get_account(account_id)
        except ValueError:
            return None

    def _contribution_pace(self, account_id: str, today: date) -> dict[str, object]:
        """Calculate monthly intentional allocation pace; adjustments are excluded."""

        monthly: dict[tuple[int, int], int] = {}
        for event_date, amount in self._contribution_events(account_id):
            if event_date <= today:
                key = (event_date.year, event_date.month)
                monthly[key] = monthly.get(key, 0) + amount
        if len(monthly) < self.MIN_HISTORY_MONTHS:
            return {"is_sufficient": False, "monthly_amount": None, "months": len(monthly)}
        return {"is_sufficient": True, "monthly_amount": sum(monthly.values()) / len(monthly), "months": len(monthly)}

    def _contribution_events(self, account_id: str) -> list[tuple[date, int]]:
        """Return intentional linked events; Adjustment records are omitted."""

        events: list[tuple[date, int]] = []
        for transaction in self._get_sheet_service().get_transactions():
            if str(transaction.get("account_id") or "").strip() != account_id:
                continue
            event_date = self._parse_event_date(transaction.get("date"))
            if event_date is None:
                continue
            transaction_type = str(transaction.get("type") or "").lower()
            if transaction_type == "income":
                events.append((event_date, self._amount(transaction)))
            elif transaction_type == "expense":
                events.append((event_date, -self._amount(transaction)))
        for movement in self._get_sheet_service().get_account_movements():
            if str(movement.get("movement_type") or "").lower() != "transfer":
                continue
            event_date = self._parse_event_date(movement.get("date"))
            if event_date is None:
                continue
            amount = self._amount(movement)
            if str(movement.get("to_account_id") or "").strip() == account_id:
                events.append((event_date, amount))
            if str(movement.get("from_account_id") or "").strip() == account_id:
                events.append((event_date, -amount))
        return events

    @staticmethod
    def _required_monthly_contribution(remaining: int, deadline: date | None,
                                       today: date) -> float | None:
        """Return required allocation per inclusive calendar month."""

        if deadline is None or deadline < today:
            return None
        months = (deadline.year - today.year) * 12 + deadline.month - today.month + 1
        return remaining / months

    @staticmethod
    def _calculate_health(*, current: int, target: int, deadline: date | None,
                          reference_date: date, required_monthly: float | None,
                          pace: Mapping[str, object]) -> str:
        """Return calculated health without mutating lifecycle status."""

        if current >= target:
            return "Achieved"
        if deadline is not None and deadline < reference_date:
            return "Overdue"
        if deadline is None or required_monthly is None:
            return "No Deadline"
        if not bool(pace["is_sufficient"]):
            return "Insufficient Allocation History"
        ratio = float(pace["monthly_amount"]) / required_monthly if required_monthly else 0
        if ratio >= 1:
            return "On Track"
        if ratio >= 0.8:
            return "At Risk"
        return "Off Track"

    @staticmethod
    def _orphaned_summary(goal: Goal) -> dict[str, object]:
        """Retain a historical Goal safely when its Account is unavailable."""

        return {
            "goal": goal, "account": None, "current_progress": None,
            "remaining_amount": None, "progress_percent": None,
            "required_monthly_contribution": None,
            "contribution_pace": {"is_sufficient": False, "monthly_amount": None, "months": 0},
            "health": "Account Unavailable",
        }

    @staticmethod
    def _validate_target_amount(value: int | float | str) -> int:
        """Validate a positive whole-number Goal target."""

        if isinstance(value, bool):
            raise ValueError("Target Goal harus berupa angka.")
        if isinstance(value, float):
            if not isfinite(value) or not value.is_integer():
                raise ValueError("Target Goal harus berupa angka bulat.")
            value = int(value)
        try:
            amount = int(str(value).strip().replace(".", "").replace(",", ""))
        except (TypeError, ValueError) as error:
            raise ValueError("Target Goal harus berupa angka.") from error
        if amount <= 0:
            raise ValueError("Target Goal harus lebih dari nol.")
        return amount

    @staticmethod
    def _validate_priority(value: str) -> str:
        """Normalize and validate one supported Goal priority."""

        priority = str(value).strip().lower()
        if priority not in GOAL_PRIORITIES:
            raise ValueError("Prioritas Goal tidak valid.")
        return priority

    @staticmethod
    def _parse_deadline(value: str | None) -> date | None:
        """Parse an optional ISO deadline without fabricating a value."""

        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_event_date(value: object) -> date | None:
        """Parse a persisted event date for monthly pace aggregation."""

        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _amount(record: Mapping[str, object]) -> int:
        """Normalize a persisted numeric value without clamping signed effects."""

        return int(str(record.get("amount") or 0).replace(".", "").replace(",", ""))

    def _get_sheet_service(self) -> SheetService:
        """Return the lazily initialized Sheets repository dependency."""

        if self._sheet_service is None:
            self._sheet_service = SheetService()
        return self._sheet_service

    @staticmethod
    def _now_text() -> str:
        """Return a local timestamp for Goal metadata."""

        return datetime.now().isoformat(timespec="seconds")
