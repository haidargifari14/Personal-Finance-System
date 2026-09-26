"""Safe integration health checks for the Settings page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from config import BOT_TOKEN, SPREADSHEET_NAME, WORKSHEET_NAME
from services.google_credentials import get_google_credentials_status
from services.sheet_service import SheetService

IntegrationState = Literal[
    "Connected",
    "Disconnected",
    "Error",
    "Not Configured",
]


@dataclass(frozen=True)
class IntegrationStatus:
    """Represent safe, user-facing information about one integration."""

    name: str
    state: IntegrationState
    details: dict[str, str]
    message: str | None = None
    checked_at: datetime | None = None


class IntegrationService:
    """Check configured external integrations without exposing credentials."""

    def get_telegram_status(self) -> IntegrationStatus:
        """Return Telegram configuration state without creating a bot instance."""

        if not BOT_TOKEN:
            return IntegrationStatus(
                name="Telegram Bot",
                state="Not Configured",
                details={"Bot username": "Not available"},
                message="Telegram configuration was not found.",
            )
        if not self._is_valid_telegram_token(BOT_TOKEN):
            return IntegrationStatus(
                name="Telegram Bot",
                state="Error",
                details={"Bot username": "Not available"},
                message="Telegram configuration is invalid.",
            )
        return IntegrationStatus(
            name="Telegram Bot",
            state="Disconnected",
            details={
                "Bot username": "Not available from configuration",
                "Configuration": "Available",
            },
            message="Run a connection test to recheck the configured bot token.",
        )

    def test_telegram_connection(self) -> IntegrationStatus:
        """Lightly validate Telegram configuration without starting polling."""

        status = self.get_telegram_status()
        if status.state != "Disconnected":
            return status
        return IntegrationStatus(
            name=status.name,
            state="Connected",
            details=status.details,
            message="Telegram configuration is available. Bot polling runs separately.",
            checked_at=datetime.now(),
        )

    def get_google_sheets_status(self) -> IntegrationStatus:
        """Return Google Sheets configuration state before a live health check."""

        credential_status = get_google_credentials_status()
        if not SPREADSHEET_NAME or not WORKSHEET_NAME or credential_status == "MISSING":
            return IntegrationStatus(
                name="Google Sheets",
                state="Not Configured",
                details={
                    "Spreadsheet": SPREADSHEET_NAME or "Not configured",
                    "Worksheet": WORKSHEET_NAME or "Not configured",
                    "Credentials": "Not configured",
                },
                message="Google Sheets configuration or credentials were not found.",
            )
        credential_source = {
            "ENVIRONMENT": "Environment variable",
            "LOCAL_FILE": "Local credential file",
        }[credential_status]
        return IntegrationStatus(
            name="Google Sheets",
            state="Disconnected",
            details={
                "Spreadsheet": SPREADSHEET_NAME,
                "Worksheet": WORKSHEET_NAME,
                "Credentials": credential_source,
            },
            message="Run a connection test to verify spreadsheet access.",
        )

    def test_google_sheets_connection(self) -> IntegrationStatus:
        """Verify configured worksheet read access without modifying sheet data."""

        status = self.get_google_sheets_status()
        if status.state == "Not Configured":
            return status
        try:
            sheet_service = SheetService()
            sheet_service.worksheet().row_values(1)
        except Exception:
            return IntegrationStatus(
                name="Google Sheets",
                state="Error",
                details=status.details,
                message="Unable to access the configured spreadsheet.",
            )
        return IntegrationStatus(
            name="Google Sheets",
            state="Connected",
            details=status.details,
            message="The configured worksheet can be read successfully.",
            checked_at=datetime.now(),
        )

    @staticmethod
    def _is_valid_telegram_token(token: str) -> bool:
        """Perform a minimal, secret-safe structural token validation."""

        identifier, separator, secret = token.partition(":")
        return bool(separator and identifier.isdigit() and secret.strip())
