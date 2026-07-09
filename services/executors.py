# services/executors.py

"""
Исполнители задач для пайплайна.
Каждый исполнитель имеет метод execute() с единым интерфейсом.
"""

from aiogram.types import Message, BufferedInputFile

from services.fusionbrain_api import generate
from logger import log_function_call, log_info, log_error


class TextExecutor:
    """
    Исполнитель для текстовых задач.

    Отправляет текстовое сообщение пользователю в Telegram.
    """

    @log_function_call
    async def execute(self, message: Message, text: str):
        """
        Отправляет текст пользователю.

        Args:
            message: Объект сообщения Telegram
            text: Текст для отправки
        """
        await message.answer(text)


class ImageExecutor:
    """
    Исполнитель для задач генерации изображений.

    Генерирует изображение по промпту через локальный сервер
    и отправляет его пользователю.
    """

    @log_function_call
    async def execute(self, message: Message, prompt: str):
        """
        Генерирует изображение по промпту и отправляет пользователю.

        Args:
            message: Объект сообщения Telegram
            prompt: Промпт для генерации (на английском языке)

        Raises:
            Exception: Если генерация не удалась
        """
        log_info(f"ImageExecutor: промпт для картинки: {prompt[:50]}...")
        await message.answer(f"🎨 Генерирую картинку по запросу: {prompt}")

        try:
            image_bytes = generate(prompt)
            log_info(f"ImageExecutor: картинка сгенерирована, размер {len(image_bytes)} байт")

            image_file = BufferedInputFile(image_bytes, filename="generated.png")
            await message.answer_photo(
                image_file,
                caption="🖼️ Сгенерированное изображение"
            )
            log_info("ImageExecutor: картинка отправлена пользователю")

        except Exception as e:
            log_error(f"ImageExecutor: ошибка генерации: {e}")
            await message.answer(f"❌ Ошибка генерации: {str(e)}")