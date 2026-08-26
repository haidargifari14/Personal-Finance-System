from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import traceback

from keyboards.confirm_keyboard import get_confirm_keyboard
from keyboards.account_keyboard import get_account_keyboard
from keyboards.main_menu import get_main_menu
from keyboards.post_save_keyboard import get_post_save_keyboard
from services.finance_service import FinanceService
from services.account_service import AccountService
from states.finance_state import FinanceState

router = Router()


async def prompt_account_selection(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Show active Accounts after a Telegram transaction category is selected."""

    accounts = AccountService().list_active_accounts()
    if not accounts:
        await state.clear()
        if callback.message:
            await callback.message.edit_text(
                "Belum ada akun aktif. Buat akun terlebih dahulu melalui Dashboard → Profile → Accounts."
            )
        return

    await state.set_state(FinanceState.waiting_account)
    if callback.message:
        await callback.message.edit_text(
            "Pilih akun:",
            reply_markup=get_account_keyboard(accounts),
        )


@router.callback_query(FinanceState.waiting_account, F.data.startswith("account:"))
async def select_account(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Store one active Account ID, then continue with the existing amount step."""

    account_id = str(callback.data).removeprefix("account:")
    try:
        AccountService().validate_active_account(account_id)
    except ValueError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.update_data(account_id=account_id)
    await state.set_state(FinanceState.waiting_amount)
    if callback.message:
        await callback.message.edit_text("Masukkan nominal")
    await callback.answer()


@router.message(FinanceState.waiting_amount, F.text)
async def receive_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = FinanceService.validate_amount(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(amount=amount)
    await state.set_state(FinanceState.waiting_note)
    await message.answer(
        "Masukkan catatan\n\natau ketik\n\n/skip"
    )


async def show_confirmation(
    message: Message,
    state: FSMContext,
    note: str,
) -> None:
    await state.update_data(note=note)

    data = await state.get_data()

    await message.answer(
        FinanceService.build_summary(data),
        reply_markup=get_confirm_keyboard(),
    )


@router.message(FinanceState.waiting_note, Command("skip"))
async def skip_note(
    message: Message,
    state: FSMContext,
) -> None:
    await show_confirmation(
        message,
        state,
        "",
    )


@router.message(
    FinanceState.waiting_note,
    lambda message: bool(message.text)
    and message.text.casefold() == "lewati",
)
async def skip_note_with_text(
    message: Message,
    state: FSMContext,
) -> None:
    await show_confirmation(
        message,
        state,
        "",
    )


@router.message(FinanceState.waiting_note, F.text)
async def receive_note(
    message: Message,
    state: FSMContext,
) -> None:
    await show_confirmation(
        message,
        state,
        message.text.strip(),
    )


@router.callback_query(F.data == "confirm_save")
async def confirm_save(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    data = await state.get_data()

    try:
        FinanceService().save_transaction(
            transaction_date=None,
            transaction_type=str(data["transaction_type"]),
            category=str(data["category"]),
            amount=data["amount"],
            note=str(data["note"]),
            account_id=str(data["account_id"]),
        )

    except ValueError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    except Exception as e:
        print("\n========== ERROR SAVING TRANSACTION ==========")
        traceback.print_exc()
        print(e)
        print("==============================================\n")

        await callback.answer(
            "Gagal menyimpan transaksi. Coba lagi.",
            show_alert=True,
        )
        return

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "✅ Transaksi berhasil disimpan.",
            reply_markup=get_post_save_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "new_transaction")
async def start_new_transaction(
    callback: CallbackQuery,
) -> None:

    if callback.message:
        await callback.message.edit_text(
            "Silakan pilih menu",
            reply_markup=get_main_menu(),
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_save")
async def cancel_save(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Transaksi dibatalkan.\n\nSilakan pilih menu berikutnya.",
            reply_markup=get_main_menu(),
        )

    await callback.answer()
