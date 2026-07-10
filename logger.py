# logger.py

"""
Логирование — встроенный модуль Python для логов.
Не print(), а нормальная система с уровнями (INFO, ERROR, WARNING).
"""

import inspect
import logging
import time
from functools import wraps
from typing import Callable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
    ]
)

logger = logging.getLogger(__name__)


def log_function_call(func: Callable) -> Callable:
    """
    Универсальный декоратор для логирования вызовов функций.
    Автоматически определяет, синхронная функция или асинхронная.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"➡️ Вход в {func_name}()")
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"✅ {func_name}() завершена за {elapsed:.3f}с")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func_name}() упала за {elapsed:.3f}с: {type(e).__name__}: {e}")
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"➡️ Вход в {func_name}()")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"✅ {func_name}() завершена за {elapsed:.3f}с")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func_name}() упала за {elapsed:.3f}с: {type(e).__name__}: {e}")
            raise

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def log_handler(func: Callable) -> Callable:
    """
    Декоратор для хэндлеров aiogram.
    """

    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        text = message.text or message.caption or "[без текста]"
        logger.info(f"📨 Пользователь {user_id}: {text[:100]}{'...' if len(text) > 100 else ''}")

        start_time = time.time()
        try:
            result = await func(message, *args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"✅ Хэндлер {func.__name__} отработал за {elapsed:.3f}с для {user_id}")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Хэндлер {func.__name__} упал за {elapsed:.3f}с для {user_id}: {e}")
            raise

    return wrapper


def log_info(message: str):
    logger.info(message)


def log_error(message: str):
    logger.error(message)


def log_warning(message: str):
    logger.warning(message)
