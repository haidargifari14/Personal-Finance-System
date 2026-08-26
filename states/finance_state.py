from aiogram.fsm.state import State, StatesGroup


class FinanceState(StatesGroup):
    waiting_account = State()
    waiting_amount = State()
    waiting_note = State()
