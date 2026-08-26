from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.income_keyboard import get_income_keyboard
from handlers.finance import prompt_account_selection
from services.category_definitions import INCOME_CATEGORIES
from states.finance_state import FinanceState


router = Router()


@router.callback_query(F.data == "income")
async def show_income_categories(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Pilih kategori pemasukan:",
            reply_markup=get_income_keyboard(),
        )
    await callback.answer()


INCOME_CALLBACKS = {
    f"income:{index}": category
    for index, category in enumerate(INCOME_CATEGORIES)
}


@router.callback_query(F.data.in_(INCOME_CALLBACKS))
async def select_income_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    category = INCOME_CALLBACKS[callback.data]
    await state.update_data(transaction_type="income", category=category)
    await prompt_account_selection(callback, state)
    await callback.answer()
