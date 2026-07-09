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
from logger import log_info
from middlewares.ratelimit import RateLimitMiddleware
from services.queue import task_queue
from services.alert_service import alert_checker


async def main():
    load_db()
    log_info("База данных загружена")

    dp.message.middleware(RateLimitMiddleware(min_interval=RATE_LIMIT_INTERVAL_SECONDS))
    log_info("Middleware защиты от спама подключён")

    dp.include_router(poll_router)
    dp.include_router(commands_router)
    dp.include_router(multimodal_router)
    log_info("Хендлеры зарегистрированы")

    await task_queue.start()
    log_info("TaskQueue запущена")

    # Запускаем фоновую проверку целей
    asyncio.create_task(alert_checker(bot))
    log_info("AlertChecker запущен")

    log_info("Бот запущен")
    print("🤖 Бот запущен! Данные сохраняются в БД.")
    print("Нажми Ctrl+C для остановки.")

    try:
        await dp.start_polling(bot)
    finally:
        await task_queue.stop()
        log_info("TaskQueue остановлена")


if __name__ == "__main__":
    asyncio.run(main())