# services/classifier.py

"""
Классификация намерений пользователя через YandexGPT + fallback-словари.
"""

from core import sdk
from logger import log_function_call, log_info, log_error, log_warning

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

# Ключевые слова для быстрой проверки (без вызова YandexGPT)
CRYPTO_KEYWORDS = [
    "биткоин", "биткойн", "биток", "btc",
    "эфир", "eth",
    "usdt", "тетер", "tether",
]

CURRENCY_KEYWORDS = [
    "доллар", "бакс",
    "евро",
    "рубль", "рубля", "рублей", "рублю",
    "тенге",
    "юань",
    "гривна", "гривны",
]


@log_function_call
async def classify_intent(text: str) -> str:
    """
    Классифицирует намерение пользователя по тексту.
    Использует YandexGPT с fallback-словарями для валют и криптовалют.

    Args:
        text: Текст сообщения пользователя

    Returns:
        Одно из: "currency", "crypto", "generate", "other"
    """
    text_lower = text.lower()

    # --- Шаг 1: проверка по словарям (быстрый и надёжный путь) ---
    if any(word in text_lower for word in CRYPTO_KEYWORDS):
        log_info(f"Классификация (словарь): '{text[:50]}...' → crypto")
        return "crypto"

    if any(word in text_lower for word in CURRENCY_KEYWORDS):
        log_info(f"Классификация (словарь): '{text[:50]}...' → currency")
        return "currency"

    # --- Шаг 2: классификатор YandexGPT ---
    try:
        result = classifier.run(text)
        if result and len(result) > 0:
            intent = result[0].label
            confidence = result[0].confidence

            log_info(f"Классификация (GPT): '{text[:50]}...' → {intent} (уверенность {confidence:.2f})")

            if confidence < 0.5:
                log_warning(f"Низкая уверенность классификации: {confidence:.2f}, возвращаем 'other'")
                return "other"

            return intent

        log_warning(f"Классификация не дала результатов для: {text[:50]}...")
        return "other"

    except Exception as e:
        log_error(f"Ошибка классификации: {e}")
        return "other"
