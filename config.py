# config.py


"""
Файл конфигурации проекта.
Все настройки вынесены в отдельный файл для удобства параметризации.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Yandex GPT ---
YC_FOLDER_ID = os.getenv("YC_FOLDER_ID")
YC_API_KEY = os.getenv("YC_API_KEY")
MODEL_NAME = "yandexgpt-lite"
TEMPERATURE = 0.7
MAX_TOKENS = 500

# --- Локальный сервер генерации изображений ---
LOCAL_SERVER_URL = "http://127.0.0.1:8000/"

# --- База данных ---
DB_FILE = "db_backup.json"
MAX_CONTEXT_MESSAGES = 20
DEFAULT_SYSTEM_PROMPT = "Ты полезный и дружелюбный ассистент."

# --- Лимиты и защита ---
RATE_LIMIT_MESSAGES_PER_HOUR = 20
RATE_LIMIT_INTERVAL_SECONDS = 1.0

# --- Валюты и криптовалюты ---
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
CRYPTO_CURRENCY = "usd"
