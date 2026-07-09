# states/currency.py

"""
Состояния для валютно-криптовалютного FSM.
"""

from aiogram.fsm.state import StatesGroup, State


class CurrencyStates(StatesGroup):
    """
    Состояния для установки целей по криптовалютам.
    """
    waiting_for_target = State()          # ожидаем целевую цену
    waiting_for_confirmation = State()    # ожидаем подтверждение

