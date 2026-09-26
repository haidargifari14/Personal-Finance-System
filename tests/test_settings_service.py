"""Focused tests for durable Google Sheets settings persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.user_settings import UserSettings
from services.settings_service import SettingsPersistenceError, SettingsService


class FakeSettingsWorksheet:
    """Small in-memory worksheet fake that never contacts Google Sheets."""

    def __init__(self, rows: list[list[str]] | None = None) -> None:
        self.rows = [list(row) for row in (rows or [])]

    def row_values(self, row_number: int) -> list[str]:
        return list(self.rows[row_number - 1]) if len(self.rows) >= row_number else []

    def update(self, values: list[list[str]], range_name: str) -> None:
        if range_name == "A1:C1":
            if self.rows:
                self.rows[0] = list(values[0])
            else:
                self.rows.append(list(values[0]))
            return
        row_number = int(range_name.split(":")[0][1:])
        while len(self.rows) < row_number:
            self.rows.append(["", "", ""])
        self.rows[row_number - 1] = list(values[0])

    def append_row(self, row: list[str]) -> None:
        self.rows.append(list(row))

    def get_all_records(
        self, default_blank: object = None, **_: object
    ) -> list[dict[str, str]]:
        if not self.rows:
            return []
        headers = self.rows[0]
        return [dict(zip(headers, row, strict=False)) for row in self.rows[1:]]


class FailingSettingsWorksheet:
    """Worksheet fake that represents an unavailable Google Sheets service."""

    @staticmethod
    def row_values(_: int) -> list[str]:
        raise OSError("unavailable")


class SettingsServiceTests(unittest.TestCase):
    """Verify settings remain typed, unique, and durable through one worksheet."""

    def setUp(self) -> None:
        self.worksheet = FakeSettingsWorksheet()
        self.service = SettingsService(worksheet=self.worksheet)

    def test_empty_worksheet_initializes_and_writes_new_setting(self) -> None:
        self.assertEqual(self.service.get_monthly_spending_limit(), 0)
        self.assertEqual(self.worksheet.rows[0], ["key", "value", "updated_at"])
        self.service.save_monthly_spending_limit(250_000)
        self.assertEqual(self.service.get_monthly_spending_limit(), 250_000)
        self.assertEqual(len(self.worksheet.rows), 2)

    def test_existing_key_updates_its_row(self) -> None:
        self.service.save_monthly_spending_limit(100)
        self.service.save_monthly_spending_limit(200)
        self.assertEqual(len(self.worksheet.rows), 2)
        self.assertEqual(json.loads(self.worksheet.rows[1][1]), 200)

    def test_json_values_preserve_practical_types(self) -> None:
        profile = UserSettings(name="Ada", language="Indonesian", payday=15)
        self.service.save(profile)
        self.service.save_saving_candidates({"Makan": True, "Transport": False})
        self.assertEqual(self.service.load().name, "Ada")
        self.assertEqual(self.service.load().payday, 15)
        self.assertEqual(
            self.service.get_saving_candidates(["Makan", "Transport"]),
            {"Makan": True, "Transport": False},
        )
        payload, _ = self.service._load_entries()
        self.assertIsInstance(payload["saving_candidates"], dict)
        self.assertIsInstance(payload["payday"], int)

    def test_missing_key_and_invalid_limit_behavior_remain_compatible(self) -> None:
        self.assertEqual(
            self.service.get_saving_candidates(["Makan"]), {"Makan": False}
        )
        self.assertEqual(self.service.get_monthly_spending_limit(), 0)
        with self.assertRaises(ValueError):
            self.service.save_monthly_spending_limit(-1)

    def test_local_migration_runs_once_without_deleting_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "settings.json"
            source.write_text(
                json.dumps({"name": "Ada", "monthly_spending_limit": 500_000}),
                encoding="utf-8",
            )
            service = SettingsService(source, self.worksheet)
            result = service.migrate_local_settings()
            self.assertEqual(result, {"migrated": True, "reason": "migrated", "count": 2})
            self.assertTrue(source.exists())
            self.assertEqual(service.load().name, "Ada")
            self.assertEqual(service.get_monthly_spending_limit(), 500_000)
            self.assertEqual(
                service.migrate_local_settings()["reason"], "remote_not_empty"
            )

    def test_migration_never_overwrites_non_empty_remote_settings(self) -> None:
        self.service.save_monthly_spending_limit(100)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "settings.json"
            source.write_text(json.dumps({"monthly_spending_limit": 999}), encoding="utf-8")
            result = SettingsService(source, self.worksheet).migrate_local_settings()
        self.assertEqual(result["reason"], "remote_not_empty")
        self.assertEqual(self.service.get_monthly_spending_limit(), 100)

    def test_google_sheets_failures_are_clear(self) -> None:
        with self.assertRaisesRegex(SettingsPersistenceError, "Unable to initialize"):
            SettingsService(worksheet=FailingSettingsWorksheet()).load()

    def test_existing_public_api_is_available(self) -> None:
        for name in (
            "load",
            "save",
            "get_saving_candidates",
            "save_saving_candidates",
            "get_monthly_spending_limit",
            "save_monthly_spending_limit",
        ):
            self.assertTrue(callable(getattr(self.service, name)))


if __name__ == "__main__":
    unittest.main()
