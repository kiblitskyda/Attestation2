# main.py
"""
Точка входа. Инициализация и запуск бота.
"""

import asyncio

from config import RATE_LIMIT_INTERVAL_SECONDS
from core import bot, dp
from database import load_db
from handlers.commands import router as commands_router
from handlers.multimodal import router as multimodal_router
from handlers.poll import router as poll_router
from handlers.currency import router as currency_router
from logger import log_info
from middlewares.ratelimit import RateLimitMiddleware
from services.queue import task_queue
from services.alert_service import alert_checker


async def main():
    """Собирает всё вместе и запускает."""

    # 1. Загружаем базу данных
    load_db()
    log_info("База данных загружена")

    # 2. Подключаем защиту от спама
    dp.message.middleware(RateLimitMiddleware(min_interval=RATE_LIMIT_INTERVAL_SECONDS))
    log_info("Middleware защиты от спама подключён")

    # 3. Подключаем обработчики
    dp.include_router(poll_router)
    dp.include_router(commands_router)
    dp.include_router(currency_router)
    dp.include_router(multimodal_router)
    log_info("Хендлеры зарегистрированы")

    # 4. Запускаем асинхронную очередь
    await task_queue.start()
    log_info("TaskQueue запущена")

    # 5. Создаём событие для остановки alert_checker
    alert_stop_event = asyncio.Event()

    # 6. Запускаем фоновую проверку целей
    asyncio.create_task(alert_checker(bot, alert_stop_event))
    log_info("AlertChecker запущен")

    # 7. Запускаем бота
    log_info("Бот запущен")
    print("🤖 Бот запущен! Данные сохраняются в БД.")
    print("Нажми Ctrl+C для остановки.")

    try:
        await dp.start_polling(bot)
    finally:
        # Сигналим alert_checker'у остановиться
        alert_stop_event.set()
        await task_queue.stop()
        log_info("TaskQueue остановлена")


if __name__ == "__main__":
    asyncio.run(main())

