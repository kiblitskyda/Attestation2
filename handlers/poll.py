# handlers/poll.py

"""
Обработчики для FSM-опроса.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from states.poll import Poll
from database import get_user, save_db
from logger import log_info, log_handler

router = Router()

# --- КЛАВИАТУРА ДЛЯ ОТМЕНЫ ОПРОСА ---
cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отменить опрос", callback_data="cancel_poll")]
])


# --- ЗАПУСК ОПРОСА ---

@router.message(Command("poll"))
@log_handler
async def cmd_start(message: Message, state: FSMContext):
    """
    Запускает опрос: переводит пользователя в состояние Poll.name
    и задаёт первый вопрос.
    """
    await state.set_state(Poll.name)
    await message.answer(
        "📝 Давайте познакомимся!\n\n"
        "Как вас зовут? (Введите имя)",
        reply_markup=cancel_keyboard
    )
    log_info(f"Пользователь {message.from_user.id} начал опрос")


# --- ОТМЕНА ОПРОСА ЧЕРЕЗ КОМАНДУ ---

@router.message(Command("cancel"))
@log_handler
async def cmd_cancel(message: Message, state: FSMContext):
    """
    Отменяет опрос через команду /cancel.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Вы не проходите опрос.")
        return

    await state.clear()
    await message.answer(
        "❌ Опрос отменён. Если захотите пройти снова — отправьте /poll."
    )
    log_info(f"Пользователь {message.from_user.id} отменил опрос через команду")


# --- ОТМЕНА ОПРОСА ЧЕРЕЗ КНОПКУ ---

@router.callback_query(lambda c: c.data == "cancel_poll")
@log_handler
async def process_cancel_poll(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку 'Отменить опрос'.
    """
    await callback.answer()
    current_state = await state.get_state()
    if current_state is None:
        await callback.message.edit_text("❌ Вы не проходите опрос.")
        return

    await state.clear()
    await callback.message.edit_text("❌ Опрос отменён. Если захотите пройти снова — отправьте /poll.")
    log_info(f"Пользователь {callback.from_user.id} отменил опрос через кнопку")


# --- ОБРАБОТЧИКИ СОСТОЯНИЙ ---

@router.message(Poll.name, F.text)
@log_handler
async def process_name(message: Message, state: FSMContext):
    """
    Сохраняет имя, переходит к Poll.age.
    """
    await state.update_data(name=message.text)
    await state.set_state(Poll.age)
    await message.answer(
        "Сколько вам лет? (Введите число)",
        reply_markup=cancel_keyboard
    )


@router.message(Poll.age, F.text)
@log_handler
async def process_age(message: Message, state: FSMContext):
    """
    Сохраняет возраст, переходит к Poll.city.
    """
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите число (например, 25).")
        return

    await state.update_data(age=message.text)
    await state.set_state(Poll.city)
    await message.answer(
        "В каком городе вы живёте?",
        reply_markup=cancel_keyboard
    )


@router.message(Poll.city, F.text)
@log_handler
async def process_city(message: Message, state: FSMContext):
    """
    Сохраняет город, переходит к Poll.activity.
    """
    await state.update_data(city=message.text)
    await state.set_state(Poll.activity)
    await message.answer(
        "Какая ваша основная деятельность? (например, учёба, работа)",
        reply_markup=cancel_keyboard
    )


@router.message(Poll.activity, F.text)
@log_handler
async def process_activity(message: Message, state: FSMContext):
    """
    Сохраняет деятельность, сохраняет данные опроса в профиль пользователя,
    выводит резюме и завершает опрос.
    """
    await state.update_data(activity=message.text)

    # Получаем все данные из FSM
    data = await state.get_data()
    user_id = message.from_user.id

    # === НОВЫЙ БЛОК: СОХРАНЯЕМ ДАННЫЕ ОПРОСА В ПРОФИЛЬ ===
    user = get_user(user_id)
    user.poll_data = {
        "name": data.get("name", ""),
        "age": data.get("age", ""),
        "city": data.get("city", ""),
        "activity": data.get("activity", ""),
    }
    save_db()
    log_info(f"Данные опроса сохранены для {user_id}: {user.poll_data}")
    # === КОНЕЦ НОВОГО БЛОКА ===

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
@log_handler
async def process_name_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.name."""
    await message.answer("❌ Пожалуйста, введите имя текстом.")


@router.message(Poll.age)
@log_handler
async def process_age_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.age."""
    await message.answer("❌ Пожалуйста, введите возраст числом.")


@router.message(Poll.city)
@log_handler
async def process_city_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.city."""
    await message.answer("❌ Пожалуйста, введите город текстом.")


@router.message(Poll.activity)
@log_handler
async def process_activity_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии Poll.activity."""
    await message.answer("❌ Пожалуйста, введите деятельность текстом.")