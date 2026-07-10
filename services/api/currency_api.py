# services/api/currency_api.py

"""
Модуль для работы с API валют (freecurrencyapi.com).
Содержит функции для получения курсов и извлечения валют из текста.
"""

import re

import requests

from config import CURRENCY_API_KEY
from logger import log_function_call, log_error

# Таймаут для HTTP-запросов (секунды)
REQUEST_TIMEOUT = 10


def extract_currencies(text: str) -> tuple:
    """
    Извлекает из текста базовую валюту и целевую валюту.

    Args:
        text: Текст запроса пользователя

    Returns:
        Кортеж (base_currency, target_currency), например ("USD", "RUB")
    """
    text_lower = text.lower()

    currency_map = {
        "доллар": "USD", "доллара": "USD", "долларов": "USD", "бакс": "USD",
        "евро": "EUR",
        "рубль": "RUB", "рубля": "RUB", "рублей": "RUB", "рублю": "RUB", "руб": "RUB",
        "тенге": "KZT",
        "юань": "CNY",
        "гривна": "UAH", "гривны": "UAH"
    }

    found_currencies = []
    for word, code in currency_map.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            if code not in found_currencies:
                found_currencies.append(code)

    if len(found_currencies) == 0:
        return "USD", "RUB"
    elif len(found_currencies) == 1:
        return found_currencies[0], "RUB"
    else:
        return found_currencies[0], found_currencies[1]


@log_function_call
def get_exchange_rate(base_currency: str, target_currency: str) -> float:
    """
    Получает курс одной валюты к другой с помощью freecurrencyapi.com.

    Args:
        base_currency: Базовая валюта (например, "USD")
        target_currency: Целевая валюта (например, "RUB")

    Returns:
        Курс (float)

    Raises:
        Exception: Если API-ключ не настроен или запрос не удался
    """
    if not CURRENCY_API_KEY:
        raise Exception("API-ключ для курса валют не настроен. Добавьте CURRENCY_API_KEY в .env")

    url = 'https://api.freecurrencyapi.com/v1/latest'
    params = {
        'apikey': CURRENCY_API_KEY,
        'base_currency': base_currency,
        'currencies': target_currency
    }

    try:
        response = requests.get(
            url,
            params=params,
            proxies={"http": None, "https": None},
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            raise Exception(f"Ошибка запроса: {response.status_code}")

        data = response.json()
        return data['data'][target_currency]

    except requests.Timeout:
        log_error(f"Таймаут при получении курса {base_currency} → {target_currency}")
        raise Exception(f"Таймаут запроса к API валют")
    except requests.RequestException as e:
        log_error(f"Ошибка получения курса: {e}")
        raise
