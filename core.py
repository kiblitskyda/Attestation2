#core.py

"""
Ядро приложения. Создаёт объекты, нужные всем модулям.
Сам никого не импортирует (кроме config и библиотек).
"""

from aiogram import Bot, Dispatcher
from yandex_ai_studio_sdk import AIStudio

import config

# --- Telegram ---
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# --- Yandex GPT ---
sdk = AIStudio(
    folder_id=config.YC_FOLDER_ID,
    auth=config.YC_API_KEY
)

model = sdk.models.completions(config.MODEL_NAME).configure(
    temperature=config.TEMPERATURE,
    max_tokens=config.MAX_TOKENS
)