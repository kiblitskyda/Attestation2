# services/crypto_api.py

"""
Модуль для работы с API криптовалют (CoinGecko).
Содержит функции для получения курсов криптовалют и извлечения их из текста.
"""

import re
import requests

from config import CRYPTO_API_URL, CRYPTO_CURRENCY
from logger import log_error


def extract_crypto(text: str) -> str | None:
    """
    Извлекает из текста код криптовалюты (bitcoin, ethereum, tether) по словарю.
    """
    text_lower = text.lower()
    crypto_map = {
        "биткоин": "bitcoin",
        "биткойн": "bitcoin",
        "btc": "bitcoin",
        "эфир": "ethereum",
        "eth": "ethereum",
        "usdt": "tether",
    }

    for word, code in crypto_map.items():
        # Ищем слово как часть текста (без привязки к границам)
        if word in text_lower:
            return code

    return None


def get_crypto_price(crypto_id: str) -> float | None:
    """
    Получает текущую цену криптовалюты в USD через CoinGecko.

    Args:
        crypto_id: Код криптовалюты (например, "bitcoin")

    Returns:
        Цена в USD (float) или None в случае ошибки
    """
    try:
        url = CRYPTO_API_URL
        params = {'ids': crypto_id, 'vs_currencies': CRYPTO_CURRENCY}
        response = requests.get(url, params=params, proxies={"http": None, "https": None})

        if response.status_code != 200:
            return None

        data = response.json()
        return data.get(crypto_id, {}).get(CRYPTO_CURRENCY)

    except Exception as e:
        log_error(f"Ошибка получения курса криптовалюты {crypto_id}: {e}")
        return None