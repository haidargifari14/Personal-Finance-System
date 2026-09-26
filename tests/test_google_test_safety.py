"""Regression tests for the production Google Sheets test guard."""

from __future__ import annotations

import os
import unittest

import gspread

from config import SPREADSHEET_NAME
from services import google_credentials
from tests.google_test_safety import (
    BLOCKED_ACCESS_MESSAGE,
    BLOCKED_SPREADSHEET_NAME,
)


class GoogleTestSafetyTests(unittest.TestCase):
    """Verify normal tests cannot use production credentials or clients."""

    def test_google_environment_and_local_fallback_are_blocked(self) -> None:
        self.assertEqual(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"), "")
        self.assertEqual(SPREADSHEET_NAME, BLOCKED_SPREADSHEET_NAME)
        self.assertFalse(google_credentials._local_credentials_path().exists())

    def test_real_google_client_construction_fails_clearly(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Production Google access is blocked"):
            gspread.authorize(object())
        self.assertIn("fake/mocked", BLOCKED_ACCESS_MESSAGE)


if __name__ == "__main__":
    unittest.main()
