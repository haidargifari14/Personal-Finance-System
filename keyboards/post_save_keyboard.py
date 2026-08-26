from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_post_save_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Tambah Lagi", callback_data="new_transaction")],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="main_menu")],
        ]
    )
