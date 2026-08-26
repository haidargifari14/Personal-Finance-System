from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.category_definitions import INCOME_CATEGORIES


INCOME_EMOJIS = {
    "Uang Saku": "💵",
    "Gaji": "💼",
    "Freelance": "💻",
    "Reimbursement": "🔄",
    "Investasi": "📈",
    "Lainnya": "💰",
}


def get_income_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{INCOME_EMOJIS[category]} {category}",
                    callback_data=f"income:{index}",
                )
            ]
            for index, category in enumerate(INCOME_CATEGORIES)
        ]
        + [[InlineKeyboardButton(text="⬅️ Kembali", callback_data="main_menu")]]
    )
