# handlers/currency.py

"""
Обработчики для валютных и криптовалютных запросов.
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import add_alert, get_user, save_db
from logger import log_info, log_error, log_warning
from services.currency_api import extract_currencies, get_exchange_rate
from services.crypto_api import extract_crypto, get_crypto_price
from states.currency import CurrencyStates

router = Router()


# --- ОБРАБОТЧИК ВАЛЮТНЫХ ЗАПРОСОВ ---

async def handle_currency_request(message: Message, text: str):
    """
    Обрабатывает запрос на получение курса валюты.
    """
    try:
        base, target = extract_currencies(text)
        rate = get_exchange_rate(base, target)

        await message.answer(
            f"💰 **Курс валют**\n\n"
            f"1 {base} = {rate:.2f} {target}\n"
            f"(по данным freecurrencyapi.com)"
        )
        log_info(f"Пользователь {message.from_user.id}: курс {base}/{target} = {rate:.2f}")

    except Exception as e:
        log_error(f"Ошибка получения курса валют: {e}")
        await message.answer(f"❌ Ошибка получения курса: {str(e)}")


# --- ОБРАБОТЧИК КРИПТОВАЛЮТНЫХ ЗАПРОСОВ ---

async def handle_crypto_request(message: Message, text: str):
    """
    Обрабатывает запрос на получение курса криптовалюты
    или установку цели для отслеживания.
    """
    user_id = message.from_user.id
    crypto_id = extract_crypto(text)

    if not crypto_id:
        await message.answer("❌ Не удалось определить криптовалюту. Попробуйте: биткоин, эфир, usdt")
        return

    # Проверяем, хочет ли пользователь следить за криптовалютой
    if any(word in text.lower() for word in ["следить", "мониторить", "отслеживать"]):
        # Получаем текущий курс
        price = get_crypto_price(crypto_id)
        if not price:
            await message.answer("❌ Не удалось получить текущий курс. Попробуйте позже.")
            return

        # Сохраняем данные во временное хранилище FSM
        await state.update_data(coin=crypto_id, current_price=price)
        await state.set_state(CurrencyStates.waiting_for_target)

        await message.answer(
            f"Отлично! Текущий курс {crypto_id.title()} = {price:.2f} USD.\n"
            f"Какую цель установим? (введите число)"
        )
        log_info(f"Пользователь {user_id}: начал установку цели для {crypto_id}")
        return

    # Просто запрос курса
    price = get_crypto_price(crypto_id)
    if price:
        await message.answer(
            f"🪙 **Курс криптовалюты**\n\n"
            f"1 {crypto_id.title()} = {price:.2f} USD\n"
            f"(по данным CoinGecko)"
        )
        log_info(f"Пользователь {user_id}: курс {crypto_id} = {price:.2f} USD")
    else:
        await message.answer("❌ Не удалось получить курс криптовалюты. Попробуйте позже.")


# --- FSM: ОЖИДАНИЕ ЦЕЛИ ---

@router.message(CurrencyStates.waiting_for_target, F.text)
async def process_target(message: Message, state: FSMContext):
    """
    Пользователь вводит целевую цену.
    """
    user_id = message.from_user.id

    try:
        target = float(message.text.replace(",", "").replace("$", "").strip())
        await state.update_data(target=target)
        await state.set_state(CurrencyStates.waiting_for_confirmation)

        data = await state.get_data()
        coin = data.get("coin", "криптовалюта")
        current_price = data.get("current_price", 0)

        await message.answer(
            f"Понял! Буду следить за {coin.title()}.\n"
            f"Текущий курс: {current_price:.2f} USD\n"
            f"Целевая цена: {target:.2f} USD\n\n"
            f"Подтверждаете установку цели? (Да/Нет)"
        )
        log_info(f"Пользователь {user_id}: ввёл цель {target:.2f} для {coin}")

    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например, 63000)")


@router.message(CurrencyStates.waiting_for_confirmation, F.text)
async def process_confirmation(message: Message, state: FSMContext):
    """
    Пользователь подтверждает или отменяет установку цели.
    """
    user_id = message.from_user.id
    answer = message.text.lower()

    if answer in ["да", "yes", "конечно", "ок"]:
        data = await state.get_data()
        coin = data.get("coin")
        target = data.get("target")

        if coin and target:
            # Сохраняем цель в базу данных
            add_alert(user_id, coin, target)
            await message.answer(
                f"✅ Готово! Я уведомлю вас, когда {coin.title()} достигнет {target:.2f} USD."
            )
            log_info(f"Пользователь {user_id}: цель для {coin} установлена на {target:.2f} USD")
        else:
            await message.answer("❌ Что-то пошло не так. Попробуйте начать заново.")

    else:
        await message.answer("❌ Отмена. Если передумаете — просто скажите 'Хочу следить за биткоином'.")
        log_info(f"Пользователь {user_id}: отменил установку цели")

    # Очищаем состояние
    await state.clear()


# --- ОБРАБОТКА НЕКОРРЕКТНОГО ВВОДА В FSM ---

@router.message(CurrencyStates.waiting_for_target)
async def process_target_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии waiting_for_target."""
    await message.answer("❌ Пожалуйста, введите число (например, 63000)")


@router.message(CurrencyStates.waiting_for_confirmation)
async def process_confirmation_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии waiting_for_confirmation."""
    await message.answer("❌ Пожалуйста, ответьте 'Да' или 'Нет'.")