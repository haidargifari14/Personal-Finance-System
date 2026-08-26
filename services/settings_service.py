"""Local persistence for Profile planning and Saving Candidate preferences."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from models.user_settings import UserSettings


class SettingsService:
    """Persist local Profile preferences without owning domain data.

    V2 Account balances, Goals, Transactions, and Forecast inputs never read
    this service as a source of truth. The Monthly Spending Limit is the sole
    planning preference consumed by Forecast/Recommendation. Existing legacy
    keys remain untouched so an upgrade does not corrupt local configuration.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize an optional storage location for local preferences."""

        root = Path(__file__).resolve().parents[1]
        self._storage_path = storage_path or root / "data" / "settings.json"

    def load(self) -> UserSettings:
        """Load Personal profile values while tolerating legacy JSON fields."""

        payload = self._load_payload()
        setting_names = {field.name for field in fields(UserSettings)}
        try:
            return UserSettings(
                **{key: value for key, value in payload.items() if key in setting_names}
            )
        except TypeError:
            return UserSettings()

    def save(self, settings: UserSettings) -> UserSettings:
        """Persist Personal profile changes without deleting unknown JSON keys."""

        if settings.name and not settings.name.strip():
            raise ValueError("Name cannot contain only spaces.")
        payload = self._load_payload()
        payload.update(settings.to_dict())
        self._write_payload(payload)
        return settings

    def get_saving_candidates(
        self,
        categories: list[str] | tuple[str, ...],
    ) -> dict[str, bool]:
        """Return explicit Saving Candidate preferences for requested categories."""

        raw_candidates = self._load_payload().get("saving_candidates", {})
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
        payload = self._load_payload()
        payload["saving_candidates"] = normalized
        self._write_payload(payload)
        return normalized

    def get_monthly_spending_limit(self) -> int:
        """Return the configured non-negative Monthly Spending Limit.

        A missing, malformed, or zero value disables Spending Risk analysis.
        This reads only local JSON and never accesses Google Sheets.
        """

        raw_limit = self._load_payload().get("monthly_spending_limit", 0)
        if isinstance(raw_limit, bool):
            return 0
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return 0
        return max(limit, 0)

    def save_monthly_spending_limit(self, limit: int) -> int:
        """Persist a non-negative Monthly Spending Limit in local JSON only."""

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("Monthly Spending Limit must be zero or a positive amount.")
        payload = self._load_payload()
        payload["monthly_spending_limit"] = limit
        self._write_payload(payload)
        return limit

    def _load_payload(self) -> dict[str, object]:
        """Load a safe raw payload while tolerating missing or corrupt JSON."""

        if not self._storage_path.exists():
            return {}
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_payload(self, payload: dict[str, object]) -> None:
        """Atomically write local preferences without mutating domain sheets."""

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._storage_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary_path.replace(self._storage_path)
