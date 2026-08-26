import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.expense import router as expense_router
from handlers.finance import router as finance_router
from handlers.income import router as income_router
from handlers.report import router as report_router
from handlers.start import router as start_router


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN tidak ditemukan.")

    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_routers(
        start_router,
        expense_router,
        income_router,
        finance_router,
        report_router,
    )
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
