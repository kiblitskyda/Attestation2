# services/classifier.py

"""
Классификация намерений пользователя через YandexGPT.
"""

from typing import Optional

from core import sdk
from logger import log_info, log_error, log_warning

# Создаём классификатор один раз при импорте
classifier = sdk.models.text_classifiers("yandexgpt").configure(
    task_description=(
        "Определи намерение пользователя по его сообщению. Верни ТОЛЬКО одно слово.\n\n"
        "currency — если сообщение про курс фиатных валют (доллар, евро, рубль, тенге, юань). "
        "Примеры: 'курс доллара', 'сколько стоит евро', 'рубль к тенге'.\n\n"
        "crypto — если сообщение про курс криптовалют. Слова-маркеры: биткоин, биток, btc, "
        "эфир, eth, usdt, тетер. Примеры: 'курс биткоина', 'сколько стоит биток', 'btc to usd'.\n\n"
        "generate — если пользователь просит сгенерировать текст или картинку. "
        "Примеры: 'нарисуй кота', 'расскажи про космос'.\n\n"
        "other — всё остальное (приветствия, общие вопросы)."
    ),
    labels=["currency", "crypto", "generate", "other"]
)


async def classify_intent(text: str) -> str:
    """
    Классифицирует намерение пользователя по тексту.

    Args:
        text: Текст сообщения пользователя

    Returns:
        Одно из: "currency", "crypto", "generate", "other"
    """
    try:
        result = classifier.run(text)
        # Берём первый (наиболее вероятный) результат
        if result and len(result) > 0:
            intent = result[0].label
            confidence = result[0].confidence

            log_info(f"Классификация: '{text[:50]}...' → {intent} (уверенность {confidence:.2f})")

            # Если уверенность ниже порога — возвращаем "other"
            if confidence < 0.5:
                log_warning(f"Низкая уверенность классификации: {confidence:.2f}, возвращаем 'other'")
                return "other"

            return intent

        log_warning(f"Классификация не дала результатов для: {text[:50]}...")
        return "other"

    except Exception as e:
        log_error(f"Ошибка классификации: {e}")
        return "other"