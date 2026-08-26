from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main_menu import get_main_menu


router = Router()


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    first_name = message.from_user.first_name if message.from_user else "teman"
    await message.answer(
        f"Halo {first_name} 👋\n\nSilakan pilih menu",
        reply_markup=get_main_menu(),
    )


@router.callback_query(lambda callback: callback.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Silakan pilih menu",
            reply_markup=get_main_menu(),
        )
    await callback.answer()
