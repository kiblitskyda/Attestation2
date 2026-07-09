# handlers/currency.py

"""
Обработчики для валютных и криптовалютных запросов.
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import add_alert, get_user, save_db
from logger import log_info, log_error, log_warning
from services.currency_api import extract_currencies, get_exchange_rate
from services.crypto_api import extract_crypto, get_crypto_price
from states.currency import CurrencyStates

router = Router()

# --- КЛАВИАТУРА ДЛЯ ПОДТВЕРЖДЕНИЯ ---
confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")
    ]
])


# --- ОБРАБОТЧИК ВАЛЮТНЫХ ЗАПРОСОВ ---

async def handle_currency_request(message: Message, text: str, state: FSMContext):
    """
    Обрабатывает запрос на получение курса валюты
    или установку цели для отслеживания.
    """
    user_id = message.from_user.id

    # Проверяем, хочет ли пользователь следить за валютой
    if any(word in text.lower() for word in ["следить", "мониторить", "отслеживать"]):
        base, target = extract_currencies(text)
        try:
            rate = get_exchange_rate(base, target)
            await state.update_data(currency_base=base, currency_target=target, current_rate=rate)
            await state.set_state(CurrencyStates.waiting_for_target)

            await message.answer(
                f"Отлично! Текущий курс {base} = {rate:.2f} {target}.\n"
                f"Какую цель установим? (введите число, например, 80)"
            )
            log_info(f"Пользователь {user_id}: начал установку цели для {base}/{target}")
            return
        except Exception as e:
            await message.answer(f"❌ Не удалось получить текущий курс: {str(e)}")
            return

    # Обычный запрос курса
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

async def handle_crypto_request(message: Message, text: str, state: FSMContext):
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
        price = get_crypto_price(crypto_id)
        if not price:
            await message.answer("❌ Не удалось получить текущий курс. Попробуйте позже.")
            return

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
    Пользователь вводит целевую цену (для валюты или криптовалюты).
    """
    user_id = message.from_user.id

    try:
        target = float(message.text.replace(",", "").replace("$", "").strip())
        await state.update_data(target=target)
        await state.set_state(CurrencyStates.waiting_for_confirmation)

        data = await state.get_data()

        # Определяем, что отслеживаем: валюту или криптовалюту
        if "currency_base" in data and "currency_target" in data:
            # ВАЛЮТА
            base = data["currency_base"]
            target_currency = data["currency_target"]
            current_rate = data.get("current_rate", 0)

            await message.answer(
                f"Понял! Буду следить за курсом {base} к {target_currency}.\n"
                f"Текущий курс: 1 {base} = {current_rate:.2f} {target_currency}\n"
                f"Целевой курс: 1 {base} = {target:.2f} {target_currency}\n\n"
                f"Подтверждаете установку цели?",
                reply_markup=confirm_keyboard
            )
            log_info(f"Пользователь {user_id}: ввёл цель {target:.2f} для {base}/{target_currency}")

        elif "coin" in data:
            # КРИПТОВАЛЮТА
            coin = data["coin"]
            current_price = data.get("current_price", 0)

            await message.answer(
                f"Понял! Буду следить за {coin.title()}.\n"
                f"Текущий курс: {current_price:.2f} USD\n"
                f"Целевая цена: {target:.2f} USD\n\n"
                f"Подтверждаете установку цели?",
                reply_markup=confirm_keyboard
            )
            log_info(f"Пользователь {user_id}: ввёл цель {target:.2f} для {coin}")

        else:
            await message.answer("❌ Что-то пошло не так. Попробуйте начать заново.")
            await state.clear()

    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например, 80)")


# --- ОБРАБОТЧИК НАЖАТИЯ НА КНОПКИ ---

@router.callback_query(lambda c: c.data in ["confirm_yes", "confirm_no"])
async def process_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопки подтверждения цели.
    """
    user_id = callback.from_user.id
    await callback.answer()

    if callback.data == "confirm_yes":
        data = await state.get_data()

        # Определяем, что сохранять
        if "currency_base" in data and "currency_target" in data:
            # ВАЛЮТА
            base = data["currency_base"]
            target_currency = data["currency_target"]
            target = data.get("target")
            item = f"{base}/{target_currency}"
            alert_type = "currency"

            if base and target_currency and target:
                # === ПРОВЕРКА НА ДУБЛИ ===
                user = get_user(user_id)
                for alert in user.alerts:
                    if (alert.get("active") and
                        alert.get("type") == alert_type and
                        alert.get("item") == item and
                        alert.get("target") == target):
                        await callback.message.edit_text(
                            f"⚠️ Вы уже следите за курсом {item} с целью {target:.2f}. Повторная цель не создана."
                        )
                        await state.clear()
                        return
                # === КОНЕЦ ПРОВЕРКИ ===

                # Сохраняем цель
                add_alert(user_id, item, target, alert_type=alert_type)
                await callback.message.edit_text(
                    f"✅ Готово! Я уведомлю вас, когда курс {base} к {target_currency} достигнет {target:.2f}."
                )
                log_info(f"Пользователь {user_id}: цель для {base}/{target_currency} установлена на {target:.2f}")
            else:
                await callback.message.edit_text("❌ Что-то пошло не так. Попробуйте начать заново.")

        elif "coin" in data:
            # КРИПТОВАЛЮТА
            coin = data["coin"]
            target = data.get("target")
            item = coin
            alert_type = "crypto"

            if coin and target:
                # === ПРОВЕРКА НА ДУБЛИ ===
                user = get_user(user_id)
                for alert in user.alerts:
                    if (alert.get("active") and
                        alert.get("type") == alert_type and
                        alert.get("item") == item and
                        alert.get("target") == target):
                        await callback.message.edit_text(
                            f"⚠️ Вы уже следите за {coin} с целью {target:.2f}. Повторная цель не создана."
                        )
                        await state.clear()
                        return
                # === КОНЕЦ ПРОВЕРКИ ===

                # Сохраняем цель
                add_alert(user_id, coin, target, alert_type=alert_type)
                await callback.message.edit_text(
                    f"✅ Готово! Я уведомлю вас, когда {coin.title()} достигнет {target:.2f} USD."
                )
                log_info(f"Пользователь {user_id}: цель для {coin} установлена на {target:.2f} USD")
            else:
                await callback.message.edit_text("❌ Что-то пошло не так. Попробуйте начать заново.")

        else:
            await callback.message.edit_text("❌ Что-то пошло не так. Попробуйте начать заново.")

    else:  # confirm_no
        await callback.message.edit_text("❌ Отмена. Если передумаете — просто скажите 'Хочу следить за...'.")
        log_info(f"Пользователь {user_id}: отменил установку цели")

    await state.clear()


# --- ОБРАБОТКА НЕКОРРЕКТНОГО ВВОДА В FSM ---

@router.message(CurrencyStates.waiting_for_target)
async def process_target_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии waiting_for_target."""
    await message.answer("❌ Пожалуйста, введите число (например, 63000)")


@router.message(CurrencyStates.waiting_for_confirmation)
async def process_confirmation_invalid(message: Message):
    """Если пользователь отправил не текст в состоянии waiting_for_confirmation."""
    await message.answer("❌ Пожалуйста, используйте кнопки для подтверждения.")