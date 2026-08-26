from datetime import date
from math import isfinite
from typing import Any, Mapping

from services.category_definitions import is_standard_category
from services.account_service import AccountService
from services.sheet_service import SheetService
from services.transaction_schema import normalize_account_id, normalize_transaction


class FinanceService:
    """Business rules for building and displaying finance transactions."""

    TRANSACTION_LABELS = {
        "expense": "Pengeluaran",
        "income": "Pemasukan",
    }
    MONTH_NAMES = (
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember",
    )

    def __init__(self, sheet_service: SheetService | None = None) -> None:
        """Initialize FinanceService with an optional SheetService dependency."""

        self._sheet_service = sheet_service

    @staticmethod
    def validate_amount(text: str) -> int:
        normalized = text.strip().replace(".", "").replace(",", "").replace(" ", "")
        try:
            amount = int(normalized)
        except ValueError as error:
            raise ValueError("Nominal harus berupa angka.") from error

        if amount <= 0:
            raise ValueError("Nominal harus lebih dari nol.")
        return amount

    @staticmethod
    def format_rupiah(amount: int) -> str:
        prefix = "-" if amount < 0 else ""
        return f"{prefix}Rp{abs(amount):,}".replace(",", ".")

    @classmethod
    def build_summary(cls, data: Mapping[str, Any]) -> str:
        transaction_type = str(data["transaction_type"])
        category = str(data["category"])
        amount = int(data["amount"])
        note = str(data.get("note") or "-")
        label = cls.TRANSACTION_LABELS[transaction_type]

        return (
            "Konfirmasi transaksi\n\n"
            f"Jenis\n{label}\n\n"
            f"Kategori\n{category}\n\n"
            f"Nominal\n{cls.format_rupiah(amount)}\n\n"
            f"Catatan\n{note}"
        )

    @staticmethod
    def build_transaction(
        data: Mapping[str, Any],
        transaction_date: date | None = None,
    ) -> dict[str, Any]:
        required_fields = {"transaction_type", "category", "amount", "note"}
        if not required_fields.issubset(data):
            raise ValueError("Data transaksi tidak lengkap.")

        return normalize_transaction({
            "date": (transaction_date or date.today()).isoformat(),
            "type": str(data["transaction_type"]),
            "category": str(data["category"]),
            "amount": int(data["amount"]),
            "note": str(data["note"]),
            "transaction_id": data.get("transaction_id"),
            "account_id": data.get("account_id"),
            "expense_type": data.get("expense_type"),
            "coverage_months": data.get("coverage_months"),
        }, generate_missing_id=True)

    def save_transaction(
        self,
        *,
        transaction_date: date | None,
        transaction_type: str,
        category: str,
        amount: int | float | str | None,
        note: str | None = None,
        account_id: str | None = None,
        expense_type: str | None = None,
        coverage_months: int | float | str | None = None,
    ) -> dict[str, Any]:
        """Validate, build, and persist one finance transaction."""

        transaction = self._build_validated_transaction(
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            category=category,
            amount=amount,
            note=note,
            account_id=account_id,
            expense_type=expense_type,
            coverage_months=coverage_months,
            default_date_if_missing=True,
            require_standard_category=True,
            require_account=True,
            transaction_id=None,
        )
        self._get_sheet_service().append(transaction)
        return transaction

    def prepare_transaction(
        self,
        *,
        transaction_date: date | None,
        transaction_type: str,
        category: str,
        amount: int | float | str | None,
        note: str | None = None,
        account_id: str | None = None,
        expense_type: str | None = None,
        coverage_months: int | float | str | None = None,
    ) -> dict[str, Any]:
        """Validate and build a transaction without persisting it."""

        return self._build_validated_transaction(
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            category=category,
            amount=amount,
            note=note,
            account_id=account_id,
            expense_type=expense_type,
            coverage_months=coverage_months,
            default_date_if_missing=False,
            require_standard_category=False,
            require_account=False,
            transaction_id=None,
        )

    def update_transaction(
        self,
        transaction_id: str,
        *,
        transaction_date: date | None,
        transaction_type: str,
        category: str,
        amount: int | float | str | None,
        note: str | None = None,
        account_id: str | None = None,
        expense_type: str | None = None,
        coverage_months: int | float | str | None = None,
    ) -> dict[str, Any]:
        """Validate, build, and update one existing finance transaction."""

        transaction = self._build_validated_transaction(
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            category=category,
            amount=amount,
            note=note,
            account_id=account_id,
            expense_type=expense_type,
            coverage_months=coverage_months,
            default_date_if_missing=False,
            require_standard_category=False,
            require_account=False,
            transaction_id=transaction_id,
        )
        transaction["transaction_id"] = transaction_id
        self._get_sheet_service().update(transaction_id, transaction)
        return transaction

    def delete_transaction(self, transaction_id: str) -> None:
        """Delete one existing transaction using its immutable identity."""

        self._get_sheet_service().delete(transaction_id)

    def _build_validated_transaction(
        self,
        *,
        transaction_date: date | None,
        transaction_type: str,
        category: str,
        amount: int | float | str | None,
        note: str | None,
        account_id: str | None,
        expense_type: str | None,
        coverage_months: int | float | str | None,
        default_date_if_missing: bool,
        require_standard_category: bool,
        require_account: bool,
        transaction_id: str | None,
    ) -> dict[str, Any]:
        """Validate form values and build a transaction ready for persistence."""

        # Telegram has no date-input step. A missing date at the save boundary
        # therefore means "today" in the application's local date convention.
        if transaction_date is None and not default_date_if_missing:
            raise ValueError("Tanggal transaksi wajib dipilih.")
        normalized_date = transaction_date or date.today()

        normalized_type = transaction_type.strip().lower()
        if normalized_type not in self.TRANSACTION_LABELS:
            raise ValueError("Jenis transaksi tidak valid.")

        normalized_category = category.strip()
        if not normalized_category:
            raise ValueError("Kategori transaksi wajib diisi.")
        if require_standard_category and not is_standard_category(
            normalized_type,
            normalized_category,
        ):
            raise ValueError("Kategori transaksi tidak valid.")

        normalized_account_id = normalize_account_id(account_id)
        self._validate_transaction_account(
            normalized_account_id,
            require_account=require_account,
            transaction_id=transaction_id,
        )

        transaction = self.build_transaction(
            {
                "transaction_type": normalized_type,
                "category": normalized_category,
                "amount": self._validate_amount_value(amount),
                "note": (note or "").strip(),
                "account_id": normalized_account_id,
                "expense_type": expense_type,
                "coverage_months": coverage_months,
            },
            transaction_date=normalized_date,
        )
        return transaction

    def _validate_transaction_account(
        self,
        account_id: str | None,
        *,
        require_account: bool,
        transaction_id: str | None,
    ) -> None:
        """Enforce Account ownership while preserving historical null records."""

        if account_id is None:
            if require_account:
                raise ValueError("Akun wajib dipilih untuk transaksi baru.")
            return

        account_service = AccountService(self._get_sheet_service())
        try:
            account_service.validate_active_account(account_id)
        except ValueError:
            if self._is_unchanged_archived_account(transaction_id, account_id):
                return
            raise

    def _is_unchanged_archived_account(
        self,
        transaction_id: str | None,
        account_id: str,
    ) -> bool:
        """Allow an archived Account only for its existing historical link."""

        if not transaction_id:
            return False
        return any(
            transaction.get("transaction_id") == transaction_id
            and normalize_account_id(transaction.get("account_id")) == account_id
            for transaction in self._get_sheet_service().get_transactions()
        )

    def _get_sheet_service(self) -> SheetService:
        """Return the lazily initialized Google Sheets repository."""

        if self._sheet_service is None:
            self._sheet_service = SheetService()

        return self._sheet_service

    @classmethod
    def _validate_amount_value(cls, amount: int | float | str | None) -> int:
        """Validate numeric form input without changing text-input validation."""

        if amount is None:
            raise ValueError("Nominal transaksi wajib diisi.")
        if isinstance(amount, bool):
            raise ValueError("Nominal harus berupa angka.")
        if isinstance(amount, float):
            if not isfinite(amount) or not amount.is_integer():
                raise ValueError("Nominal harus berupa angka bulat.")
            amount = int(amount)
        if isinstance(amount, int):
            return cls.validate_amount(str(amount))

        return cls.validate_amount(amount)

    @staticmethod
    def daily_summary(
        transactions: list[Mapping[str, Any]],
        target_date: date | None = None,
    ) -> dict[str, int]:
        date_text = (target_date or date.today()).isoformat()
        filtered = [
            transaction
            for transaction in transactions
            if str(transaction.get("date", "")) == date_text
        ]
        return FinanceService._calculate_totals(filtered)

    @staticmethod
    def monthly_summary(
        transactions: list[Mapping[str, Any]],
        target_date: date | None = None,
    ) -> dict[str, Any]:
        selected_date = target_date or date.today()
        prefix = selected_date.strftime("%Y-%m")
        filtered = [
            transaction
            for transaction in transactions
            if str(transaction.get("date", "")).startswith(prefix)
        ]
        summary: dict[str, Any] = FinanceService._calculate_totals(filtered)
        categories: dict[str, int] = {}
        for transaction in filtered:
            if str(transaction.get("type", "")) != "expense":
                continue
            category = str(transaction.get("category", "Lainnya"))
            categories[category] = categories.get(category, 0) + FinanceService._amount(transaction)

        summary["month_name"] = FinanceService.MONTH_NAMES[selected_date.month - 1]
        summary["top_expense_categories"] = sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        return summary

    @staticmethod
    def _calculate_totals(transactions: list[Mapping[str, Any]]) -> dict[str, int]:
        income = sum(
            FinanceService._amount(transaction)
            for transaction in transactions
            if str(transaction.get("type", "")) == "income"
        )
        expense = sum(
            FinanceService._amount(transaction)
            for transaction in transactions
            if str(transaction.get("type", "")) == "expense"
        )
        return {
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "count": len(transactions),
        }

    @staticmethod
    def _amount(transaction: Mapping[str, Any]) -> int:
        raw_amount = str(transaction.get("amount", "0"))
        return int(raw_amount.replace(".", "").replace(",", "").replace(" ", ""))
