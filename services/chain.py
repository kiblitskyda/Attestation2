# services/chain.py

"""
Цепочка обязанностей (Chain of Responsibility) для обработки задач.
Каждый исполнитель сам решает, может ли он обработать задачу.
Если нет — передаёт дальше по цепочке.
ImageExecutor использует асинхронную очередь для фоновой генерации.
"""

from typing import Optional, Dict, Any

from aiogram.types import Message, BufferedInputFile

from services.fusionbrain_api import generate
from services.queue import task_queue
from logger import log_function_call, log_info, log_error


class BaseExecutor:
    """
    Базовый класс для всех исполнителей в цепочке.
    """

    def __init__(self):
        self._next: Optional["BaseExecutor"] = None

    def set_next(self, next_executor: "BaseExecutor") -> "BaseExecutor":
        """
        Устанавливает следующего исполнителя в цепочке.

        Args:
            next_executor: Следующий исполнитель

        Returns:
            Следующий исполнитель (для удобства цепочки)
        """
        self._next = next_executor
        return next_executor

    async def handle(self, message: Message, task: Dict[str, Any]) -> bool:
        """
        Обрабатывает задачу. Если не может — передаёт дальше.

        Args:
            message: Объект сообщения Telegram
            task: Словарь с задачей (например, {"text": "..."} или {"image": "..."})

        Returns:
            True, если задача обработана, иначе False
        """
        if self._next:
            return await self._next.handle(message, task)
        return False


class TextExecutor(BaseExecutor):
    """
    Исполнитель для текстовых задач.
    """

    @log_function_call
    async def handle(self, message: Message, task: Dict[str, Any]) -> bool:
        """
        Обрабатывает задачу, если в ней есть ключ "text".
        """
        if "text" in task:
            text = task["text"]
            log_info(f"TextExecutor: отправка текста длиной {len(text)} символов")
            await message.answer(text)
            return True

        # Если не текст — передаём дальше
        return await super().handle(message, task)


class ImageExecutor(BaseExecutor):
    """
    Исполнитель для задач генерации изображений.
    Использует асинхронную очередь для фоновой генерации.
    """

    @log_function_call
    async def handle(self, message: Message, task: Dict[str, Any]) -> bool:
        """
        Обрабатывает задачу, если в ней есть ключ "image".
        """
        if "image" in task:
            prompt = task["image"]
            user_id = message.from_user.id

            log_info(f"ImageExecutor: промпт для картинки: {prompt[:50]}...")

            # 1. Сразу отвечаем пользователю, что задача принята
            await message.answer(
                f"🎨 Ваша картинка по запросу «{prompt[:50]}...» поставлена в очередь. "
                f"Она будет готова через некоторое время."
            )

            # 2. Ставим задачу в очередь
            await task_queue.add_task(
                user_id=user_id,
                message=message,
                task_type="image",
                data=prompt,
                handler=self._generate_and_send_image
            )

            log_info(f"ImageExecutor: задача на генерацию для {user_id} поставлена в очередь")
            return True

        # Если не изображение — передаём дальше
        return await super().handle(message, task)

    @log_function_call
    async def _generate_and_send_image(self, message: Message, prompt: str):
        """
        Функция-обработчик для фоновой генерации.
        Вызывается воркером из очереди.
        """
        try:
            image_bytes = await generate(prompt)  # ← добавлен await
            log_info(f"ImageExecutor: картинка сгенерирована, размер {len(image_bytes)} байт")

            image_file = BufferedInputFile(image_bytes, filename="generated.png")
            await message.answer_photo(
                image_file,
                caption="🖼️ Ваша картинка готова!"
            )
            log_info("ImageExecutor: картинка отправлена пользователю")

        except Exception as e:
            log_error(f"ImageExecutor: ошибка генерации: {e}")
            await message.answer(f"❌ Ошибка генерации: {str(e)}")


def build_chain() -> BaseExecutor:
    """
    Строит цепочку обязанностей.

    Порядок: TextExecutor → ImageExecutor.
    Можно легко менять порядок или добавлять новых исполнителей.

    Returns:
        Корневой исполнитель (первый в цепочке)
    """
    text_executor = TextExecutor()
    image_executor = ImageExecutor()

    # Строим цепочку: TextExecutor → ImageExecutor
    text_executor.set_next(image_executor)

    return text_executor