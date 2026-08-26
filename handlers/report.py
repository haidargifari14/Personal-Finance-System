from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.report_keyboard import get_report_keyboard
from services.report_service import ReportService


router = Router()

@router.callback_query(F.data == "report")
async def show_report_placeholder(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.edit_text(
            "Pilih laporan yang ingin dilihat:",
            reply_markup=get_report_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "report:today")
async def show_today_report(callback: CallbackQuery) -> None:
    try:
        text = ReportService.get_today_report()
    except Exception:
        await callback.answer("Gagal memuat laporan. Coba lagi.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_report_keyboard())
    await callback.answer()


@router.callback_query(F.data == "report:month")
async def show_month_report(callback: CallbackQuery) -> None:
    try:
        text = ReportService.get_month_report()
    except Exception:
        await callback.answer("Gagal memuat laporan. Coba lagi.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(text, reply_markup=get_report_keyboard())
    await callback.answer()
