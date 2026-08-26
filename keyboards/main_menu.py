from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Pengeluaran", callback_data="expense")],
            [InlineKeyboardButton(text="💰 Pemasukan", callback_data="income")],
            [InlineKeyboardButton(text="📊 Report", callback_data="report")],
        ]
    )
