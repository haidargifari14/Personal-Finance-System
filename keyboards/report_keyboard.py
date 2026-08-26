from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Hari Ini", callback_data="report:today")],
            [InlineKeyboardButton(text="📅 Bulan Ini", callback_data="report:month")],
            [InlineKeyboardButton(text="⬅️ Kembali", callback_data="main_menu")],
        ]
    )
