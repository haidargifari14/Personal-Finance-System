"""Test-only guard that prevents accidental production Google access."""

from __future__ import annotations

import os
from pathlib import Path


BLOCKED_SPREADSHEET_NAME = "__GOOGLE_TEST_ACCESS_BLOCKED__"
BLOCKED_ACCESS_MESSAGE = (
    "Production Google access is blocked during tests. "
    "Use a fake/mocked Google Sheets client, or mark an explicit integration test."
)


def integration_tests_enabled() -> bool:
    """Return whether an explicitly authorized integration-test run was requested."""

    return os.getenv("RUN_GOOGLE_INTEGRATION_TESTS") == "1"


def install_google_test_safety_guard() -> None:
    """Block real Google credentials and clients for normal automated tests."""

    if integration_tests_enabled():
        return

    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = ""
    os.environ["SPREADSHEET_NAME"] = BLOCKED_SPREADSHEET_NAME

    import gspread
    from services import google_credentials

    google_credentials._local_credentials_path = lambda: Path(
        "__google_test_credentials_blocked__.json"
    )

    def blocked_authorize(*_: object, **__: object) -> object:
        raise RuntimeError(BLOCKED_ACCESS_MESSAGE)

    gspread.authorize = blocked_authorize
