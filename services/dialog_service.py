# services/dialog_service.py

"""
Сервис для обработки мультимодальных запросов.
Отправляет запросы в Yandex GPT и возвращает JSON-массив.
"""

from core import model
from database import get_full_context, add_to_context
from logger import log_function_call, log_error, log_info


@log_function_call
async def get_multimodal_response(user_id: int, user_input: str) -> str:
    """
    Отправляет запрос в Yandex GPT с требованием вернуть JSON-массив.

    Args:
        user_id: ID пользователя в Telegram
        user_input: Текст запроса от пользователя

    Returns:
        Сырая строка ответа от Yandex GPT
    """
    # Формируем системный промпт с инструкцией
    system_prompt = (
        "Ты — мультимодальный ассистент. Ты общаешься с пользователем на русском языке. "
        "Твоя задача — отвечать на запросы, возвращая JSON-массив.\n\n"
        "Формат ответа: массив объектов. Каждый объект имеет ОДИН ключ:\n"
        "- 'text' — для текстового ответа (всегда на русском языке).\n"
        "- 'image' — для генерации изображения (промпт ВСЕГДА на английском языке).\n\n"
        "Правила:\n"
        "1. Текстовые ответы пиши на русском языке (если пользователь написал по-русски).\n"
        "2. Промпты для изображений — строго на английском, детальные, с указанием стиля и освещения.\n"
        "3. Если запрос требует только текста — верни [{\"text\": \"ответ на русском\"}].\n"
        "4. Если запрос требует только картинки — верни [{\"image\": \"prompt in English\"}].\n"
        "5. Если запрос требует и текста, и картинки — верни [{\"text\": \"ответ на русском\"}, {\"image\": \"prompt in English\"}].\n"
        "6. НЕ добавляй пояснений, НЕ используй markdown. Только чистый JSON.\n"
        "7. Если запрос непонятен — верни [{\"text\": \"Извините, я не понял запрос. Повторите, пожалуйста.\"}].\n\n"
        "Примеры:\n"
        "Запрос: 'Привет!'\n"
        "Ответ: [{\"text\": \"Здравствуйте! Чем я могу вам помочь?\"}]\n\n"
        "Запрос: 'Нарисуй закат на море'\n"
        "Ответ: [{\"image\": \"Sunset over the sea, golden sky, waves, warm colors, realistic style\"}]\n\n"
        "Запрос: 'Расскажи про Париж и покажи Эйфелеву башню'\n"
        "Ответ: [{\"text\": \"Париж — столица Франции, известный своей архитектурой и культурой.\"}, {\"image\": \"Eiffel Tower in Paris at sunset, illuminated, beautiful sky\"}]"
    )

    # Сохраняем сообщение пользователя в контекст
    add_to_context(user_id, {"role": "user", "text": user_input})

    # Получаем полный контекст (system + история диалога)
    # Заменяем системный промпт на наш мультимодальный
    full_context = get_full_context(user_id)
    if full_context and full_context[0]["role"] == "system":
        # Меняем системный промпт на наш
        full_context[0]["text"] = system_prompt
    else:
        # Если по какой-то причине system нет — вставляем
        full_context.insert(0, {"role": "system", "text": system_prompt})

    try:
        # Отправляем запрос в модель
        result = model.run(full_context)
        response_text = result[0].text

        # Сохраняем ответ модели в контекст
        add_to_context(user_id, {"role": "assistant", "text": response_text})

        log_info(f"YandexGPT ответил: {response_text[:100]}...")
        return response_text

    except Exception as e:
        log_error(f"Ошибка при запросе к YandexGPT: {e}")
        # Возвращаем JSON с ошибкой
        error_response = '[{"text": "❌ Произошла ошибка при обработке запроса. Попробуйте позже."}]'
        add_to_context(user_id, {"role": "assistant", "text": error_response})
        return error_response

