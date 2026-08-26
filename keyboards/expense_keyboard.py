from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.category_definitions import EXPENSE_CATEGORIES


EXPENSE_EMOJIS = {
    "Makan": "🍔",
    "Transport": "🚗",
    "Belanja": "🛍️",
    "Hiburan": "🎮",
    "Kesehatan": "💊",
    "Tempat Tinggal": "🏠",
    "Tagihan & Langganan": "🧾",
    "Pendidikan": "📚",
    "Lainnya": "📦",
}


def get_expense_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EXPENSE_EMOJIS[category]} {category}",
                    callback_data=f"expense:{index}",
                )
            ]
            for index, category in enumerate(EXPENSE_CATEGORIES)
        ]
        + [[InlineKeyboardButton(text="⬅️ Kembali", callback_data="main_menu")]]
    )
