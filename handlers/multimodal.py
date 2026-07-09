# handlers/multimodal.py

"""
Обработчик мультимодальных запросов.
Принимает текстовые сообщения и запускает пайплайн (текст + картинки).
"""

import json

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import check_rate_limit
from logger import log_info, log_warning, log_error
from services.dialog_service import get_multimodal_response
from services.chain import build_chain
from services.classifier import classify_intent          # <-- НОВЫЙ ИМПОРТ
from handlers.currency import handle_currency_request, handle_crypto_request
from services.crypto_api import extract_crypto


router = Router()


@router.message(~F.text.startswith("/"))
async def handle_multimodal(message: Message, state: FSMContext):
    """
    Обрабатывает все текстовые сообщения, кроме команд.
    Сначала классифицирует намерение, затем маршрутизирует.
    """
    user_id = message.from_user.id
    user_input = message.text

    # 1. Проверка: если пользователь в опросе — пропускаем
    current_state = await state.get_state()
    if current_state and current_state.startswith("Poll:"):
        await message.answer(
            "⚠️ Вы сейчас проходите опрос. "
            "Пожалуйста, ответьте на вопросы или введите /cancel для выхода."
        )
        return

    # 2. Проверяем лимит запросов
    if not check_rate_limit(user_id):
        await message.answer("⏳ Вы превысили лимит запросов. Попробуйте позже.")
        log_warning(f"Пользователь {user_id} превысил лимит запросов")
        return

    # 3. Классифицируем намерение
    # Сначала проверяем криптовалюты по словарю
    crypto_hint = extract_crypto(user_input)
    if crypto_hint:
        intent = "crypto"
        log_info(f"Пользователь {user_id}: обнаружена криптовалюта '{crypto_hint}'")
    else:
        intent = await classify_intent(user_input)
        log_info(f"Пользователь {user_id}: намерение '{intent}'")


    # 4. Маршрутизация по намерению
    if intent in ["currency", "crypto"]:
        if intent == "currency":
            await handle_currency_request(message, user_input)
        else:  # crypto
            await handle_crypto_request(message, user_input)
        return

    # 5. Для "generate" и "other" — мультимодальный пайплайн
    # Показываем статус "печатает..."
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Получаем JSON от YandexGPT
    try:
        raw_json = await get_multimodal_response(user_id, user_input)
    except Exception as e:
        await message.answer(f"❌ Ошибка при запросе к YandexGPT: {str(e)}")
        log_warning(f"Ошибка YandexGPT для {user_id}: {e}")
        return

    # Очищаем и парсим JSON
    try:
        cleaned_json = _clean_ai_response(raw_json)
        tasks = json.loads(cleaned_json)
        log_info(f"Распарсено {len(tasks)} задач")
    except json.JSONDecodeError as e:
        log_error(f"Ошибка парсинга JSON: {e}")
        await message.answer("❌ Ошибка: ответ от ИИ не является валидным JSON.")
        return

    if not isinstance(tasks, list):
        log_error(f"Ожидался список, получен {type(tasks)}")
        await message.answer("❌ Ошибка: ожидался JSON-массив, получен объект.")
        return

    # Строим цепочку обязанностей
    chain_root = build_chain()

    # Запускаем обработку каждой задачи через цепочку
    for i, task in enumerate(tasks):
        log_info(f"Задача {i+1}/{len(tasks)}: {list(task.keys()) if isinstance(task, dict) else 'не словарь'}")
        if not isinstance(task, dict):
            await message.answer(f"⚠️ Неизвестный формат задачи: {task}")
            continue

        handled = await chain_root.handle(message, task)
        if not handled:
            log_info(f"Задача не обработана: {list(task.keys())}")
            await message.answer(f"⚠️ Неизвестный тип задачи: {list(task.keys())}")

    log_info(f"Пайплайн для {user_id} успешно выполнен")


def _clean_ai_response(raw_string: str) -> str:
    """
    Извлекает из сырой строки часть, содержащую JSON-массив.
    """
    try:
        start = raw_string.find('[')
        end = raw_string.rfind(']')
        if start != -1 and end > start:
            return raw_string[start:end + 1]
    except Exception as e:
        log_error(f"Ошибка очистки JSON: {e}")
    return "[]"