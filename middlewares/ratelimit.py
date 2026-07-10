# middlewares/ratelimit.py

"""
Middleware для ограничения частоты запросов.
"""

import time
from typing import Dict, Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from logger import log_warning


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов.
    Callback-запросы игнорируются.
    """

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_message_time: Dict[int, float] = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        # Пропускаем callback-запросы
        if hasattr(event, 'callback_query') and event.callback_query:
            return await handler(event, data)

        # Проверяем текстовые сообщения
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            current_time = time.time()

            if user_id in self.last_message_time:
                time_diff = current_time - self.last_message_time[user_id]
                if time_diff < self.min_interval:
                    await event.answer(
                        f"⏳ Подождите немного! Слишком частые сообщения. "
                        f"Повторите через {self.min_interval - time_diff:.1f} секунд."
                    )
                    log_warning(f"⛔ Спам от пользователя {user_id}: {time_diff:.2f}с")
                    return

            self.last_message_time[user_id] = current_time

        return await handler(event, data)
