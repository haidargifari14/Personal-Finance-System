"""Centralized Google service-account credential configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from google.oauth2.service_account import Credentials


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

GoogleCredentialsStatus = Literal["ENVIRONMENT", "LOCAL_FILE", "MISSING"]


class GoogleCredentialsConfigurationError(RuntimeError):
    """Raised when Google service-account credentials are not configured."""



def get_google_credentials_status() -> GoogleCredentialsStatus:
    """Return the configured credential source without exposing secret values."""

    if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return "ENVIRONMENT"
    if _local_credentials_path().is_file():
        return "LOCAL_FILE"
    return "MISSING"



def get_google_credentials() -> Credentials:
    """Load service-account credentials from the environment or local file."""

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if credentials_json:
        try:
            credentials_info = json.loads(credentials_json)
        except json.JSONDecodeError as error:
            raise GoogleCredentialsConfigurationError(
                "Google service account credentials are not configured correctly. "
                "GOOGLE_SERVICE_ACCOUNT_JSON must contain valid JSON."
            ) from error
        return Credentials.from_service_account_info(
            credentials_info,
            scopes=GOOGLE_SCOPES,
        )

    credentials_path = _local_credentials_path()
    if credentials_path.is_file():
        return Credentials.from_service_account_file(
            str(credentials_path),
            scopes=GOOGLE_SCOPES,
        )

    raise GoogleCredentialsConfigurationError(
        "Google service account credentials are not configured. Set "
        "GOOGLE_SERVICE_ACCOUNT_JSON or provide a local credentials.json file."
    )



def _local_credentials_path() -> Path:
    """Return the project-local service-account credential file path."""

    return Path(__file__).resolve().parents[1] / "credentials.json"
