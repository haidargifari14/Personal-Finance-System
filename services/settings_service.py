"""Google Sheets persistence for Profile and planning preferences."""

from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread

from config import SETTINGS_WORKSHEET_NAME, SPREADSHEET_NAME
from models.user_settings import UserSettings
from services.google_credentials import get_google_credentials


SETTINGS_HEADERS = ("key", "value", "updated_at")


class SettingsPersistenceError(RuntimeError):
    """Raised when durable Google Sheets settings cannot be read or written."""


class SettingsService:
    """Persist application settings in a dedicated Google Sheets worksheet.

    Google Sheets is the source of truth. The optional local path remains only
    as an explicit, non-destructive migration input for legacy settings.json.
    """

    def __init__(
        self,
        storage_path: Path | None = None,
        worksheet: Any | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self._storage_path = storage_path or root / "data" / "settings.json"
        self._worksheet = worksheet

    def load(self) -> UserSettings:
        """Load Personal profile values while tolerating legacy setting keys."""

        payload, _ = self._load_entries()
        setting_names = {field.name for field in fields(UserSettings)}
        try:
            return UserSettings(
                **{key: value for key, value in payload.items() if key in setting_names}
            )
        except TypeError:
            return UserSettings()

    def save(self, settings: UserSettings) -> UserSettings:
        """Persist Personal profile changes without deleting unknown settings."""

        if settings.name and not settings.name.strip():
            raise ValueError("Name cannot contain only spaces.")
        _, rows = self._load_entries()
        self._write_values(settings.to_dict(), rows)
        return settings

    def get_saving_candidates(
        self,
        categories: list[str] | tuple[str, ...],
    ) -> dict[str, bool]:
        """Return explicit Saving Candidate preferences for requested categories."""

        payload, _ = self._load_entries()
        raw_candidates = payload.get("saving_candidates", {})
        candidates = raw_candidates if isinstance(raw_candidates, dict) else {}
        return {
            str(category): bool(candidates.get(str(category), False))
            for category in categories
            if str(category).strip()
        }

    def save_saving_candidates(self, candidates: dict[str, bool]) -> dict[str, bool]:
        """Persist candidate configuration owned by Forecast/Recommendation."""

        normalized: dict[str, bool] = {}
        for category, enabled in candidates.items():
            name = str(category).strip()
            if not name:
                raise ValueError("Nama kategori Saving Candidate tidak boleh kosong.")
            if not isinstance(enabled, bool):
                raise ValueError("Nilai Saving Candidate harus true atau false.")
            normalized[name] = enabled
        _, rows = self._load_entries()
        self._write_values({"saving_candidates": normalized}, rows)
        return normalized

    def get_monthly_spending_limit(self) -> int:
        """Return the configured non-negative Monthly Spending Limit."""

        payload, _ = self._load_entries()
        raw_limit = payload.get("monthly_spending_limit", 0)
        if isinstance(raw_limit, bool):
            return 0
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return 0
        return max(limit, 0)

    def save_monthly_spending_limit(self, limit: int) -> int:
        """Persist a non-negative Monthly Spending Limit in Google Sheets."""

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("Monthly Spending Limit must be zero or a positive amount.")
        _, rows = self._load_entries()
        self._write_values({"monthly_spending_limit": limit}, rows)
        return limit

    def migrate_local_settings(self) -> dict[str, object]:
        """Import legacy local JSON once, only when remote Settings is empty.

        The local file is retained. Repeating a successful migration is safe
        because the non-empty remote worksheet is never overwritten.
        """

        payload, rows = self._load_entries()
        if payload or rows:
            return {"migrated": False, "reason": "remote_not_empty", "count": 0}
        local_payload = self._load_local_payload()
        if not local_payload:
            return {"migrated": False, "reason": "local_settings_empty", "count": 0}
        self._write_values(local_payload, rows)
        return {"migrated": True, "reason": "migrated", "count": len(local_payload)}

    def _load_entries(self) -> tuple[dict[str, object], dict[str, int]]:
        worksheet = self._get_worksheet()
        try:
            records = worksheet.get_all_records(
                default_blank=None,
                numericise_ignore=["all"],
            )
        except Exception as error:  # noqa: BLE001 - Google client exceptions vary.
            raise SettingsPersistenceError(
                "Unable to read Google Sheets settings."
            ) from error

        payload: dict[str, object] = {}
        rows: dict[str, int] = {}
        for row_number, record in enumerate(records, start=2):
            key = record.get("key")
            if not isinstance(key, str) or not key.strip():
                raise SettingsPersistenceError(
                    "Google Sheets Settings contains an invalid setting key."
                )
            key = key.strip()
            if key in rows:
                raise SettingsPersistenceError(
                    "Google Sheets Settings contains duplicate setting keys."
                )
            try:
                payload[key] = json.loads(record.get("value", ""))
            except (TypeError, json.JSONDecodeError) as error:
                raise SettingsPersistenceError(
                    f"Google Sheets Settings contains an invalid value for '{key}'."
                ) from error
            rows[key] = row_number
        return payload, rows

    def _write_values(self, values: dict[str, object], rows: dict[str, int]) -> None:
        worksheet = self._get_worksheet()
        timestamp = datetime.now().isoformat()
        try:
            for key, value in values.items():
                serialized = json.dumps(value, ensure_ascii=False)
                row = rows.get(key)
                if row is None:
                    worksheet.append_row([key, serialized, timestamp])
                else:
                    worksheet.update([[key, serialized, timestamp]], f"A{row}:C{row}")
        except Exception as error:  # noqa: BLE001 - Google client exceptions vary.
            raise SettingsPersistenceError(
                "Unable to save Google Sheets settings."
            ) from error

    def _get_worksheet(self) -> Any:
        if self._worksheet is not None:
            self._ensure_worksheet_schema(self._worksheet)
            return self._worksheet
        if not SPREADSHEET_NAME:
            raise SettingsPersistenceError(
                "Google Sheets settings are unavailable because SPREADSHEET_NAME is not configured."
            )
        try:
            credentials = get_google_credentials()
            client = gspread.authorize(credentials)
            spreadsheet = client.open(SPREADSHEET_NAME)
            try:
                worksheet = spreadsheet.worksheet(SETTINGS_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=SETTINGS_WORKSHEET_NAME,
                    rows=1000,
                    cols=len(SETTINGS_HEADERS),
                )
            self._ensure_worksheet_schema(worksheet)
        except SettingsPersistenceError:
            raise
        except Exception as error:  # noqa: BLE001 - Google client exceptions vary.
            raise SettingsPersistenceError(
                "Unable to access Google Sheets settings."
            ) from error
        self._worksheet = worksheet
        return worksheet

    @staticmethod
    def _ensure_worksheet_schema(worksheet: Any) -> None:
        try:
            headers = list(worksheet.row_values(1))
            if not headers:
                worksheet.update([list(SETTINGS_HEADERS)], "A1:C1")
                return
        except Exception as error:  # noqa: BLE001 - Google client exceptions vary.
            raise SettingsPersistenceError(
                "Unable to initialize Google Sheets Settings."
            ) from error
        if headers != list(SETTINGS_HEADERS):
            raise SettingsPersistenceError(
                "Google Sheets Settings has an unsupported header structure."
            )

    def _load_local_payload(self) -> dict[str, object]:
        """Read legacy local JSON only as an explicit migration source."""

        if not self._storage_path.exists():
            return {}
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}
