# states/poll.py

"""
Состояния для FSM-опроса пользователя.
"""

from aiogram.fsm.state import StatesGroup, State


class Poll(StatesGroup):
    """
    Группа состояний для анкетирования.
    """
    name = State()  # ожидаем имя
    age = State()  # ожидаем возраст
    city = State()  # ожидаем город
    activity = State()  # ожидаем деятельность
