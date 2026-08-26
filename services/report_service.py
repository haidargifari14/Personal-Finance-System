"""Business logic for Telegram reports and transaction exports."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from services.finance_service import FinanceService
from services.sheet_service import SheetService
from services.transaction_schema import EXPORT_COLUMNS as TRANSACTION_EXPORT_COLUMNS


class ReportService:
    """Build report text from persisted finance transactions."""

    EXPORT_COLUMNS = TRANSACTION_EXPORT_COLUMNS

    CATEGORY_EMOJIS = {
        "Makan": "🍔",
        "Transport": "🚗",
        "Belanja": "🛍️",
        "Hiburan": "🎮",
        "Kesehatan": "💊",
        "Lainnya": "📦",
    }

    @classmethod
    def get_today_report(cls) -> str:
        """Build the report for transactions recorded today."""
        summary = FinanceService.daily_summary(SheetService().get_transactions())
        return (
            "📊 Hari Ini\n\n"
            f"Pemasukan\n{FinanceService.format_rupiah(summary['income'])}\n\n"
            f"Pengeluaran\n{FinanceService.format_rupiah(summary['expense'])}\n\n"
            f"Saldo\n{FinanceService.format_rupiah(summary['balance'])}\n\n"
            f"Total transaksi\n{summary['count']}"
        )

    @classmethod
    def get_month_report(cls) -> str:
        """Build the report for transactions recorded this month."""
        summary = FinanceService.monthly_summary(SheetService().get_transactions())
        text = (
            f"📊 {summary['month_name']}\n\n"
            f"Pemasukan\n{FinanceService.format_rupiah(summary['income'])}\n\n"
            f"Pengeluaran\n{FinanceService.format_rupiah(summary['expense'])}\n\n"
            f"Saldo\n{FinanceService.format_rupiah(summary['balance'])}"
        )
        categories = summary["top_expense_categories"]
        if categories:
            text += "\n\nKategori terbesar\n\n" + "\n\n".join(
                f"{cls.CATEGORY_EMOJIS.get(category, '📦')} {category}\n"
                f"{FinanceService.format_rupiah(amount)}"
                for category, amount in categories
            )
        return text

    @classmethod
    def prepare_transaction_export(cls, transactions: pd.DataFrame) -> pd.DataFrame:
        """Return filtered transactions with stable, user-facing export columns."""

        export_data = pd.DataFrame(index=transactions.index)
        raw_dates = transactions.get("date")
        if raw_dates is None:
            export_data["Date"] = ""
        else:
            dates = pd.to_datetime(raw_dates, errors="coerce")
            export_data["Date"] = dates.dt.strftime("%Y-%m-%d").fillna("")
        export_data["Transaction ID"] = cls._export_text(
            transactions,
            "transaction_id",
        )
        export_data["Category"] = cls._export_text(transactions, "category")
        export_data["Type"] = (
            cls._export_text(transactions, "type").str.strip().str.title()
        )
        export_data["Amount"] = cls._export_amount(transactions)
        export_data["Note"] = cls._export_text(transactions, "note")
        export_data["Account ID"] = cls._export_text(transactions, "account_id")
        export_data["Expense Type"] = cls._export_text(
            transactions,
            "expense_type",
        ).str.title()
        coverage = transactions.get("coverage_months")
        if coverage is None:
            export_data["Coverage Months"] = ""
        else:
            normalized_coverage = pd.to_numeric(
                coverage,
                errors="coerce",
            ).round()
            export_data["Coverage Months"] = normalized_coverage.map(
                lambda value: "" if pd.isna(value) else str(int(value))
            )
        return export_data.reindex(columns=cls.EXPORT_COLUMNS)

    @staticmethod
    def export_csv(export_data: pd.DataFrame) -> bytes:
        """Serialize prepared transaction data as a UTF-8 CSV file."""

        return export_data.to_csv(index=False).encode("utf-8-sig")

    @classmethod
    def export_excel(cls, export_data: pd.DataFrame) -> bytes:
        """Serialize prepared transaction data as a dependency-free XLSX file."""

        rows = [list(cls.EXPORT_COLUMNS), *export_data.values.tolist()]
        worksheet_rows = "".join(
            cls._excel_row(row_number, row)
            for row_number, row in enumerate(rows, start=1)
        )
        worksheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><sheetData>'
            f"{worksheet_rows}</sheetData></worksheet>"
        )

        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", cls._content_types_xml())
            workbook.writestr("_rels/.rels", cls._root_relationships_xml())
            workbook.writestr("xl/workbook.xml", cls._workbook_xml())
            workbook.writestr(
                "xl/_rels/workbook.xml.rels", cls._workbook_relationships_xml()
            )
            workbook.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        return buffer.getvalue()

    @staticmethod
    def _export_text(transactions: pd.DataFrame, column: str) -> pd.Series:
        """Return one optional transaction column as clean display text."""

        values = transactions.get(column)
        if values is None:
            return pd.Series("", index=transactions.index, dtype="object")
        return values.fillna("").astype(str).str.strip()

    @staticmethod
    def _export_amount(transactions: pd.DataFrame) -> pd.Series:
        """Return one optional amount column as a clean integer series."""

        values = transactions.get("amount")
        if values is None:
            return pd.Series(0, index=transactions.index, dtype="int64")
        return pd.to_numeric(values, errors="coerce").fillna(0).astype(int)

    @classmethod
    def _excel_row(cls, row_number: int, values: list[object]) -> str:
        """Build one XML worksheet row from export values."""

        cells = "".join(
            cls._excel_cell(row_number, column_number, value)
            for column_number, value in enumerate(values, start=1)
        )
        return f'<row r="{row_number}">{cells}</row>'

    @classmethod
    def _excel_cell(
        cls,
        row_number: int,
        column_number: int,
        value: object,
    ) -> str:
        """Build one XML Excel cell while preserving numeric amounts."""

        column_name = chr(64 + column_number)
        reference = f"{column_name}{row_number}"
        if (
            column_number == cls.EXPORT_COLUMNS.index("Amount") + 1
            and row_number > 1
        ):
            return f'<c r="{reference}" t="n"><v>{int(value)}</v></c>'

        text = escape(str(value))
        return (
            f'<c r="{reference}" t="inlineStr"><is>'
            f'<t xml:space="preserve">{text}</t></is></c>'
        )

    @staticmethod
    def _content_types_xml() -> str:
        """Return the minimal XLSX content-type manifest."""

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/'
            '2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.'
            'openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.spreadsheetml.'
            'worksheet+xml"/>'
            "</Types>"
        )

    @staticmethod
    def _root_relationships_xml() -> str:
        """Return the package relationship from root to workbook."""

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="xl/workbook.xml"/></Relationships>'
        )

    @staticmethod
    def _workbook_xml() -> str:
        """Return the minimal XLSX workbook descriptor."""

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
            '2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships"><sheets><sheet name="Transactions" '
            'sheetId="1" r:id="rId1"/></sheets></workbook>'
        )

    @staticmethod
    def _workbook_relationships_xml() -> str:
        """Return the workbook relationship to the transaction worksheet."""

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
        )
