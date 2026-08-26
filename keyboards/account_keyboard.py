"""Telegram keyboard for selecting an active Account."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.account import Account


def get_account_keyboard(accounts: list[Account]) -> InlineKeyboardMarkup:
    """Return compact account buttons that persist immutable Account IDs."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{account.account_name} — {account.account_location}",
                    callback_data=f"account:{account.account_id}",
                )
            ]
            for account in accounts
        ]
    )
