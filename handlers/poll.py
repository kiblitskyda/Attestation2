# handlers/poll.py

"""
Обработчики для FSM-опроса.
"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states.poll import Poll
from logger import log_info, log_error

router = Router()


# --- ЗАПУСК ОПРОСА ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Запускает опрос: переводит пользователя в состояние Poll.name
    и задаёт первый вопрос.
    """
    await state.set_state(Poll.name)
    await message.answer(
        "📝 Давайте познакомимся!\n\n"
        "Как вас зовут? (Введите имя)"
    )
    log_info(f"Пользователь {message.from_user.id} начал опрос")


# --- ОТМЕНА ОПРОСА ---

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """
    Отменяет опрос: очищает состояние и сообщает пользователю.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Вы не проходите опрос.")
        return

    await state.clear()
    await message.answer(
        "❌ Опрос отменён. Если захотите пройти снова — отправьте /start."
    )
    log_info(f"Пользователь {message.from_user.id} отменил опрос")


# --- ОБРАБОТЧИКИ СОСТОЯНИЙ ---

@router.message(Poll.name, F.text)
async def process_name(message: Message, state: FSMContext):
    """
    Сохраняет имя, переходит к Poll.age.
    """
    await state.update_data(name=message.text)
    await state.set_state(Poll.age)
    await message.answer("Сколько вам лет? (Введите число)")


@router.message(Poll.age, F.text)
async def process_age(message: Message, state: FSMContext):
    """
    Сохраняет возраст, переходит к Poll.city.
    """
    # Простая проверка на число
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число (например, 25).")
        return

    await state.update_data(age=message.text)
    await state.set_state(Poll.city)
    await message.answer("В каком городе вы живёте?")


@router.message(Poll.city, F.text)
async def process_city(message: Message, state: FSMContext):
    """
    Сохраняет город, переходит к Poll.activity.
    """
    await state.update_data(city=message.text)
    await state.set_state(Poll.activity)
    await message.answer("Какая ваша основная деятельность? (например, учёба, работа)")


@router.message(Poll.activity, F.text)
async def process_activity(message: Message, state: FSMContext):
    """
    Сохраняет деятельность, выводит резюме и завершает опрос.
    """
    await state.update_data(activity=message.text)

    # Получаем все данные
    data = await state.get_data()

    # Формируем резюме
    summary = (
        "✅ **Спасибо! Вот ваши ответы:**\n\n"
        f"📌 Имя: {data.get('name', '—')}\n"
        f"📌 Возраст: {data.get('age', '—')}\n"
        f"📌 Город: {data.get('city', '—')}\n"
        f"📌 Деятельность: {data.get('activity', '—')}"
    )

    await message.answer(summary)
    await state.clear()

    log_info(f"Пользователь {message.from_user.id} завершил опрос")


# --- ОБРАБОТКА НЕКОРРЕКТНОГО ВВОДА ---

@router.message(Poll.name)
async def process_name_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.name."""
    await message.answer("❌ Пожалуйста, введите имя текстом.")


@router.message(Poll.age)
async def process_age_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.age."""
    await message.answer("❌ Пожалуйста, введите возраст числом.")


@router.message(Poll.city)
async def process_city_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.city."""
    await message.answer("❌ Пожалуйста, введите город текстом.")


@router.message(Poll.activity)
async def process_activity_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.activity."""
    await message.answer("❌ Пожалуйста, введите деятельность текстом.")