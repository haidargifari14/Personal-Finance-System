from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from keyboards.expense_keyboard import get_expense_keyboard
from handlers.finance import prompt_account_selection
from services.category_definitions import EXPENSE_CATEGORIES
from states.finance_state import FinanceState


router = Router()


@router.callback_query(F.data == "expense")
async def show_expense_categories(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Pilih kategori pengeluaran:",
            reply_markup=get_expense_keyboard(),
        )
    await callback.answer()


EXPENSE_CALLBACKS = {
    f"expense:{index}": category
    for index, category in enumerate(EXPENSE_CATEGORIES)
}


@router.callback_query(F.data.in_(EXPENSE_CALLBACKS))
async def select_expense_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    category = EXPENSE_CALLBACKS[callback.data]
    await state.update_data(transaction_type="expense", category=category)
    await prompt_account_selection(callback, state)
    await callback.answer()
