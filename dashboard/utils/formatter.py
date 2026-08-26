"""
dashboard/utils/formatter.py

Utility functions for formatting values displayed
throughout the Personal Finance Dashboard.
"""

from datetime import datetime
from dashboard.utils.theme import (
    CURRENCY_SYMBOL,
    DEFAULT_DATE_FORMAT,
)


def format_currency(value: float | int) -> str:
    """
    Format number into Indonesian Rupiah.

    Example:
        1500000 -> Rp 1.500.000
    """

    return f"{CURRENCY_SYMBOL} {value:,.0f}".replace(",", ".")


def format_number(value: float | int) -> str:
    """
    Format integer with thousand separator.

    Example:
        1250000 -> 1.250.000
    """

    return f"{value:,.0f}".replace(",", ".")


def format_percent(value: float) -> str:
    """
    Format percentage.

    Example:
        12.3456 -> 12.35%
    """

    return f"{value:.2f}%"


def format_date(date_value: datetime) -> str:
    """
    Format datetime object into dashboard date format.

    Example:
        2026-08-06 -> 06 Aug 2026
    """

    return date_value.strftime(DEFAULT_DATE_FORMAT)


def format_datetime(date_value: datetime) -> str:
    """
    Format datetime with time.

    Example:
        06 Aug 2026 13:45
    """

    return date_value.strftime("%d %b %Y %H:%M")


def format_delta(value: float) -> str:
    """
    Format positive/negative delta values.

    Example:
        12.5 -> +12.50%
        -3.2 -> -3.20%
    """

    sign = "+" if value >= 0 else ""

    return f"{sign}{value:.2f}%"
