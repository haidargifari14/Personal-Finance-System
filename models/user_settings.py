"""Compatibility model for local Profile and saving-candidate settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class UserSettings:
    """Store Personal profile data plus inert legacy JSON fields safely.

    Legacy fields remain deserializable so existing settings files are never
    corrupted. V2 financial services must not consume them as financial input.
    """

    name: str = ""
    language: str = "English"
    timezone: str = "Asia/Jakarta"
    currency: str = "IDR"
    date_format: str = "DD MMM YYYY"
    theme: str = "System Default"
    default_chart_period: str = "This Month"
    monthly_income: int = 0
    current_balance: int = 0
    monthly_saving_target: int = 0
    payday: int = 1
    risk_preference: str = "Moderate"

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable settings representation."""

        return asdict(self)
