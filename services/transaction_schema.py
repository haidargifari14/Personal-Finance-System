"""Central transaction schema contract for Google Sheets and service layers."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping
from uuid import UUID, uuid4


# The order is append-only relative to the legacy worksheet.  Keeping the
# original five columns first lets the migration add the V2 identity fields
# without moving or recreating existing transactions.
TRANSACTION_FIELDS = (
    "date",
    "type",
    "category",
    "amount",
    "note",
    "transaction_id",
    "account_id",
    "expense_type",
    "coverage_months",
)

SHEET_HEADERS = {
    "date": "Tanggal",
    "type": "Jenis",
    "category": "Kategori",
    "amount": "Nominal",
    "note": "Catatan",
    "transaction_id": "Transaction ID",
    "account_id": "Account ID",
    "expense_type": "Expense Type",
    "coverage_months": "Coverage Months",
}

PHYSICAL_HEADERS = tuple(SHEET_HEADERS[field] for field in TRANSACTION_FIELDS)
LEGACY_HEADERS = PHYSICAL_HEADERS[:5]
EXPORT_COLUMNS = (
    "Transaction ID",
    "Date",
    "Type",
    "Category",
    "Amount",
    "Note",
    "Account ID",
    "Expense Type",
    "Coverage Months",
)

EXPENSE_TYPES = ("normal", "periodic", "one-off")


def new_transaction_id() -> str:
    """Return a collision-safe immutable transaction identifier."""

    return str(uuid4())


def is_valid_transaction_id(value: object) -> bool:
    """Return whether *value* is a UUID transaction identifier."""

    if not isinstance(value, str) or not value.strip():
        return False
    try:
        UUID(value.strip())
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def normalize_account_id(value: object) -> str | None:
    """Normalize an optional Account ID while preserving historical nulls."""

    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_expense_metadata(
    transaction_type: object,
    expense_type: object = None,
    coverage_months: object = None,
) -> tuple[str | None, int | None]:
    """Validate and normalize analytical Expense classification metadata.

    Historical Expense records without the newly added columns are interpreted
    as ``normal``. Income never owns Expense metadata, so both metadata fields
    are consistently cleared for Income records.

    Args:
        transaction_type: The transaction's Income or Expense type.
        expense_type: Optional Normal, Periodic, or One-off classification.
        coverage_months: Required positive whole-month coverage for Periodic.

    Raises:
        ValueError: If an Expense classification or coverage value is invalid.
    """

    normalized_type = str(transaction_type or "").strip().lower()
    if normalized_type == "income":
        return None, None
    if normalized_type != "expense":
        return None, None

    raw_expense_type = "" if expense_type is None else str(expense_type).strip().lower()
    normalized_expense_type = (
        "normal" if raw_expense_type in {"", "nan", "<na>"} else raw_expense_type
    )
    if normalized_expense_type not in EXPENSE_TYPES:
        raise ValueError("Jenis pengeluaran tidak valid.")
    if normalized_expense_type != "periodic":
        return normalized_expense_type, None

    if isinstance(coverage_months, bool) or (
        "" if coverage_months is None else str(coverage_months).strip().lower()
    ) in {
        "",
        "nan",
        "<na>",
    }:
        raise ValueError("Coverage Months wajib diisi untuk pengeluaran Periodic.")
    try:
        parsed_coverage = Decimal(str(coverage_months).strip())
    except Exception as error:  # noqa: BLE001 - worksheet values vary.
        raise ValueError("Coverage Months harus berupa angka bulat.") from error
    if parsed_coverage != parsed_coverage.to_integral_value():
        raise ValueError("Coverage Months harus berupa angka bulat.")
    coverage = int(parsed_coverage)
    if coverage < 1:
        raise ValueError("Coverage Months minimal 1.")
    return normalized_expense_type, coverage


def normalized_monthly_expense_contribution(record: Mapping[str, Any]) -> int:
    """Return one Expense's rounded monthly-discipline contribution.

    The result is analytical only. It does not replace the stored amount used
    by actual Expense totals, Account balances, or Financial Outlook liquidity.
    Periodic values use half-up Rupiah rounding after division by coverage.
    """

    expense_type, coverage_months = normalize_expense_metadata(
        record.get("type"),
        record.get("expense_type"),
        record.get("coverage_months"),
    )
    if expense_type is None or expense_type == "one-off":
        return 0
    try:
        amount = Decimal(str(record.get("amount", 0)))
    except Exception as error:  # noqa: BLE001 - imported values vary.
        raise ValueError("Nominal transaksi tidak valid.") from error
    if expense_type == "periodic":
        assert coverage_months is not None
        amount /= Decimal(coverage_months)
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def normalize_transaction(
    record: Mapping[str, Any],
    *,
    generate_missing_id: bool,
) -> dict[str, Any]:
    """Return a complete internal transaction record from legacy or V2 data.

    Args:
        record: A record using internal transaction field names.
        generate_missing_id: Whether a missing ID should receive a new UUID.

    Raises:
        ValueError: If a supplied transaction ID is invalid.
    """

    transaction_id = record.get("transaction_id")
    if transaction_id in (None, ""):
        if not generate_missing_id:
            raise ValueError("Transaction ID is required.")
        transaction_id = new_transaction_id()
    transaction_id = str(transaction_id).strip()
    if not is_valid_transaction_id(transaction_id):
        raise ValueError("Transaction ID is invalid.")

    expense_type, coverage_months = normalize_expense_metadata(
        record.get("type"),
        record.get("expense_type"),
        record.get("coverage_months"),
    )
    return {
        "date": str(record.get("date", "")).strip(),
        "type": str(record.get("type", "")).strip().lower(),
        "category": str(record.get("category", "")).strip(),
        "amount": record.get("amount"),
        "note": str(record.get("note", "") or "").strip(),
        "transaction_id": transaction_id,
        "account_id": normalize_account_id(record.get("account_id")),
        "expense_type": expense_type,
        "coverage_months": coverage_months,
    }


def records_to_sheet_rows(records: Iterable[Mapping[str, Any]]) -> list[list[Any]]:
    """Return records in the centralized physical Google Sheets column order."""

    rows: list[list[Any]] = []
    for record in records:
        rows.append(
            [
                "" if record.get(field) is None else record.get(field, "")
                for field in TRANSACTION_FIELDS
            ]
        )
    return rows


def sheet_record_to_transaction(record: Mapping[str, Any]) -> dict[str, Any]:
    """Map Google Sheets headers to the internal transaction field names."""

    transaction = {
        field: record.get(header)
        for field, header in SHEET_HEADERS.items()
    }
    expense_type, coverage_months = normalize_expense_metadata(
        transaction.get("type"),
        transaction.get("expense_type"),
        transaction.get("coverage_months"),
    )
    transaction["expense_type"] = expense_type
    transaction["coverage_months"] = coverage_months
    return transaction
