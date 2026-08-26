from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Simpan", callback_data="confirm_save")],
            [InlineKeyboardButton(text="❌ Batal", callback_data="cancel_save")],
        ]
    )
