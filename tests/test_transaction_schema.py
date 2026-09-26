"""Focused regression tests for the V2 transaction schema contract."""

from __future__ import annotations

import unittest
from datetime import date
from zipfile import ZipFile
from io import BytesIO

import pandas as pd
from config import WORKSHEET_NAME

from services.data_management_service import DataManagementService
from services.category_definitions import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    categories_for_type,
)
from services.finance_service import FinanceService
from services.report_service import ReportService
from services.sheet_service import SheetService
from services.transaction_schema import PHYSICAL_HEADERS, is_valid_transaction_id
from dashboard.components.transaction_form import _category_options
from keyboards.expense_keyboard import get_expense_keyboard
from keyboards.income_keyboard import get_income_keyboard


class _FakeWorksheet:
    """Minimal worksheet fake used to verify non-destructive schema migration."""

    def __init__(self) -> None:
        self.headers = ["Tanggal", "Jenis", "Kategori", "Nominal", "Catatan"]
        self.rows = [["2026-08-01", "expense", "Makan", "25000", "Bakso"]]

    def row_values(self, row: int) -> list[str]:
        return self.headers if row == 1 else self.rows[row - 2]

    def get_all_values(self) -> list[list[str]]:
        return [self.headers, *self.rows]

    def get_all_records(self, default_blank=None) -> list[dict[str, str | None]]:
        records = []
        for row in self.rows:
            padded = [*row, *([None] * (len(self.headers) - len(row)))]
            records.append(dict(zip(self.headers, padded, strict=True)))
        return records

    def update(self, cell_range: str, values: list[list[str]]) -> None:
        if cell_range == "F1:I1":
            self.headers.extend(values[0])
            return
        if cell_range == "F2:F2":
            self.rows[0].append(values[0][0])
            return
        raise AssertionError(f"Unexpected range: {cell_range}")


class TransactionSchemaTests(unittest.TestCase):
    """Verify UUID creation and legacy schema migration behavior."""

    def test_finance_service_generates_nullable_account_transaction(self) -> None:
        transaction = FinanceService.build_transaction(
            {
                "transaction_type": "expense",
                "category": "Makan",
                "amount": 25_000,
                "note": "Bakso",
            }
        )

        self.assertTrue(is_valid_transaction_id(transaction["transaction_id"]))
        self.assertIsNone(transaction["account_id"])
        self.assertEqual(transaction["expense_type"], "normal")
        self.assertIsNone(transaction["coverage_months"])

    def test_legacy_schema_is_extended_without_changing_financial_values(self) -> None:
        service = object.__new__(SheetService)
        worksheet = _FakeWorksheet()
        service._worksheet = worksheet
        service._create_migration_snapshot = lambda: None

        service._ensure_transaction_schema()

        self.assertEqual(worksheet.headers, list(PHYSICAL_HEADERS))
        self.assertEqual(worksheet.rows[0][:5], [
            "2026-08-01", "expense", "Makan", "25000", "Bakso",
        ])
        self.assertTrue(is_valid_transaction_id(worksheet.rows[0][5]))

        service._ensure_transaction_schema()
        self.assertEqual(len(worksheet.rows[0]), 6)

    def test_schema_migration_snapshot_is_in_memory(self) -> None:
        """Schema safeguards capture rows without creating a backup file."""

        service = object.__new__(SheetService)
        worksheet = _FakeWorksheet()
        service._worksheet = worksheet

        snapshot = service._create_migration_snapshot()

        self.assertEqual(snapshot["worksheet"], WORKSHEET_NAME)
        self.assertEqual(snapshot["rows"], [worksheet.headers, *worksheet.rows])

    def test_legacy_import_generates_id_and_keeps_account_null(self) -> None:
        service = DataManagementService()
        normalized = service._normalize_import_columns(
            pd.DataFrame(
                [{
                    "Date": "2026-08-01",
                    "Type": "expense",
                    "Category": "Makan",
                    "Amount": 25_000,
                    "Note": "Bakso",
                }]
            )
        )

        records, errors = service._validate_records(normalized.to_dict("records"))

        self.assertEqual(errors, [])
        self.assertTrue(is_valid_transaction_id(records[0]["transaction_id"]))
        self.assertIsNone(records[0]["account_id"])
        self.assertEqual(records[0]["expense_type"], "normal")
        self.assertIsNone(records[0]["coverage_months"])

    def test_export_preserves_v2_identity_fields(self) -> None:
        transaction = FinanceService.build_transaction(
            {
                "transaction_type": "income",
                "category": "Gaji",
                "amount": 1_000_000,
                "note": "Agustus",
                "account_id": "account-1",
            }
        )

        exported = ReportService.prepare_transaction_export(pd.DataFrame([transaction]))

        self.assertEqual(exported.loc[0, "Transaction ID"], transaction["transaction_id"])
        self.assertEqual(exported.loc[0, "Account ID"], "account-1")
        self.assertEqual(exported.loc[0, "Expense Type"], "")
        self.assertEqual(exported.loc[0, "Coverage Months"], "")

        csv_data = ReportService.export_csv(exported).decode("utf-8-sig")
        excel_data = ReportService.export_excel(exported)
        self.assertIn("Transaction ID", csv_data)
        self.assertIn("Account ID", csv_data)
        self.assertIn("Expense Type", csv_data)
        self.assertIn("Coverage Months", csv_data)
        with ZipFile(BytesIO(excel_data)) as workbook:
            worksheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode()
        self.assertIn("Transaction ID", worksheet_xml)
        self.assertIn("Account ID", worksheet_xml)
        imported = DataManagementService()._read_xlsx(excel_data)
        self.assertEqual(imported.loc[0, "Transaction ID"], transaction["transaction_id"])
        self.assertEqual(imported.loc[0, "Account ID"], "account-1")

    def test_periodic_metadata_survives_export_and_import(self) -> None:
        transaction = FinanceService.build_transaction(
            {
                "transaction_type": "expense",
                "category": "Tempat Tinggal",
                "amount": 16_000_000,
                "note": "Rent",
                "expense_type": "periodic",
                "coverage_months": 12,
            }
        )

        exported = ReportService.prepare_transaction_export(pd.DataFrame([transaction]))
        normalized = DataManagementService()._normalize_import_columns(exported)
        records, errors = DataManagementService()._validate_records(
            normalized.to_dict("records")
        )

        self.assertEqual(errors, [])
        self.assertEqual(records[0]["expense_type"], "periodic")
        self.assertEqual(records[0]["coverage_months"], 12)

    def test_save_transaction_rejects_missing_account_for_new_records(self) -> None:
        class FakeSheetService:
            def __init__(self) -> None:
                self.transaction = None

            def append(self, transaction: dict) -> None:
                raise AssertionError("Transactions without Accounts must not persist.")

        with self.assertRaisesRegex(ValueError, "Akun wajib dipilih"):
            FinanceService(FakeSheetService()).save_transaction(
                transaction_date=None,
                transaction_type="expense",
                category="Makan",
                amount=25_000,
                note="Bakso",
            )

    def test_standard_categories_are_type_specific(self) -> None:
        self.assertEqual(categories_for_type("expense"), EXPENSE_CATEGORIES)
        self.assertEqual(categories_for_type("INCOME"), INCOME_CATEGORIES)
        self.assertNotIn("Gaji", EXPENSE_CATEGORIES)
        self.assertNotIn("Makan", INCOME_CATEGORIES)

    def test_save_rejects_nonstandard_new_category(self) -> None:
        class FakeSheetService:
            def append(self, transaction: dict) -> None:
                raise AssertionError("Invalid categories must not be persisted.")

        with self.assertRaisesRegex(ValueError, "Kategori transaksi tidak valid"):
            FinanceService(FakeSheetService()).save_transaction(
                transaction_date=None,
                transaction_type="expense",
                category="Kategori Bebas",
                amount=25_000,
                note="",
            )

    def test_update_preparation_keeps_legacy_category_compatible(self) -> None:
        transaction = FinanceService().prepare_transaction(
            transaction_date=date(2026, 8, 1),
            transaction_type="expense",
            category="Legacy Category",
            amount=25_000,
            note="Historical value",
        )

        self.assertEqual(transaction["category"], "Legacy Category")

    def test_edit_options_keep_legacy_category_without_offering_free_text(self) -> None:
        legacy_options = _category_options(
            "Expense",
            {"type": "expense", "category": "Legacy Category"},
        )

        self.assertEqual(legacy_options[0], "Legacy Category")
        self.assertEqual(legacy_options[1:], EXPENSE_CATEGORIES)
        self.assertEqual(_category_options("Income", None), INCOME_CATEGORIES)

    def test_telegram_keyboards_use_the_central_category_vocabulary(self) -> None:
        expense_buttons = get_expense_keyboard().inline_keyboard[:-1]
        income_buttons = get_income_keyboard().inline_keyboard[:-1]

        self.assertEqual(len(expense_buttons), len(EXPENSE_CATEGORIES))
        self.assertEqual(len(income_buttons), len(INCOME_CATEGORIES))
        self.assertEqual(
            [row[0].callback_data for row in expense_buttons],
            [f"expense:{index}" for index in range(len(EXPENSE_CATEGORIES))],
        )
        self.assertEqual(
            [row[0].callback_data for row in income_buttons],
            [f"income:{index}" for index in range(len(INCOME_CATEGORIES))],
        )


if __name__ == "__main__":
    unittest.main()
