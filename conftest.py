"""Pytest configuration for safe, opt-in Google Sheets integration tests."""

from __future__ import annotations

import os

from tests.google_test_safety import install_google_test_safety_guard


def pytest_configure(config: object) -> None:
    """Register integration tests and install the default production-access block."""

    config.addinivalue_line(
        "markers",
        "integration: requires RUN_GOOGLE_INTEGRATION_TESTS=1 and may access Google",
    )
    install_google_test_safety_guard()


def pytest_collection_modifyitems(config: object, items: list[object]) -> None:
    """Skip explicitly marked Google integration tests unless the user opts in."""

    if os.getenv("RUN_GOOGLE_INTEGRATION_TESTS") == "1":
        return
    import pytest

    skip = pytest.mark.skip(
        reason="Google integration tests require RUN_GOOGLE_INTEGRATION_TESTS=1"
    )
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)
