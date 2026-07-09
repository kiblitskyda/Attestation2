# services/queue.py

"""
Асинхронная очередь для фоновой обработки задач.
"""

import asyncio
from typing import Dict, Any, Callable, Awaitable

from aiogram.types import Message

from logger import log_info, log_error, log_warning


class TaskQueue:
    """
    Очередь задач с фоновым воркером.
    """

    def __init__(self, num_workers: int = 2):
        """
        Args:
            num_workers: Количество параллельных воркеров
        """
        self.queue: asyncio.Queue = asyncio.Queue()
        self.num_workers = num_workers
        self.workers: list[asyncio.Task] = []
        self.is_running = False

    async def start(self):
        """
        Запускает воркеры.
        """
        if self.is_running:
            return

        self.is_running = True
        self.workers = [
            asyncio.create_task(self._worker(f"Worker-{i+1}"))
            for i in range(self.num_workers)
        ]
        log_info(f"TaskQueue: запущено {self.num_workers} воркеров")

    async def stop(self):
        """
        Останавливает воркеры (дожидается завершения текущих задач).
        """
        self.is_running = False
        # Ждём, пока очередь опустеет
        while not self.queue.empty():
            await asyncio.sleep(0.5)
            log_info("TaskQueue: ожидаем завершения задач...")

        for worker in self.workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        log_info("TaskQueue: все воркеры остановлены")

    async def add_task(
        self,
        user_id: int,
        message: Message,
        task_type: str,
        data: Any,
        handler: Callable[[Message, Any], Awaitable[None]]
    ):
        """
        Добавляет задачу в очередь.

        Args:
            user_id: ID пользователя (для логирования)
            message: Объект сообщения Telegram
            task_type: Тип задачи (например, "image")
            data: Данные для обработки (промпт, текст и т.д.)
            handler: Функция-обработчик (async)
        """
        await self.queue.put({
            "user_id": user_id,
            "message": message,
            "task_type": task_type,
            "data": data,
            "handler": handler
        })
        log_info(f"TaskQueue: задача {task_type} для пользователя {user_id} поставлена в очередь")

    async def _worker(self, name: str):
        """
        Воркер: забирает задачи из очереди и выполняет их.
        """
        log_info(f"TaskQueue: воркер {name} запущен")

        while self.is_running:
            try:
                # Берём задачу из очереди (с таймаутом, чтобы не блокировать остановку)
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                user_id = task["user_id"]
                message = task["message"]
                task_type = task["task_type"]
                data = task["data"]
                handler = task["handler"]

                log_info(f"TaskQueue: воркер {name} обрабатывает {task_type} для {user_id}")

                # Выполняем задачу
                await handler(message, data)

                log_info(f"TaskQueue: воркер {name} завершил {task_type} для {user_id}")

            except Exception as e:
                log_error(f"TaskQueue: ошибка в воркере {name}: {e}")
                # Отправляем сообщение об ошибке
                try:
                    await task["message"].answer(
                        f"❌ Ошибка при обработке задачи {task['task_type']}: {str(e)}"
                    )
                except Exception:
                    pass

            finally:
                self.queue.task_done()

        log_info(f"TaskQueue: воркер {name} остановлен")


# Глобальный экземпляр очереди (создаётся один раз при импорте)
task_queue = TaskQueue(num_workers=2)