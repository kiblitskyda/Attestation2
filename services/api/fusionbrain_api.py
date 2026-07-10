# services/api/fusionbrain_api.py

"""
Async-клиент для локального сервера генерации изображений.
"""

import asyncio
import base64
import json

import aiohttp

from config import LOCAL_SERVER_URL
from logger import log_function_call, log_error


@log_function_call
async def generate(prompt: str) -> bytes:
    """
    Генерирует изображение через локальный сервер (асинхронно).

    Args:
        prompt: Промпт на английском языке

    Returns:
        Байты PNG-изображения

    Raises:
        RuntimeError: Если сервер вернул ошибку генерации
    """
    # Таймаут для HTTP-запросов: 30 сек на подключение, до 10 минут на ожидание
    timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=600)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1. Получаем ID пайплайна
        try:
            async with session.get(f"{LOCAL_SERVER_URL}key/api/v1/pipelines") as resp:
                pipelines = await resp.json()
                pipeline_id = pipelines[0]["id"]
        except aiohttp.ClientError as e:
            log_error(f"Ошибка подключения к серверу генерации: {e}")
            raise RuntimeError(f"Не удалось подключиться к серверу генерации: {e}")
        except (KeyError, IndexError) as e:
            log_error(f"Неожиданный ответ от сервера генерации (pipelines): {e}")
            raise RuntimeError(f"Сервер генерации вернул неожиданный ответ: {e}")

        # 2. Ставим задачу на генерацию
        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": 512,
            "height": 512,
            "generateParams": {"query": prompt},
        }
        data = aiohttp.FormData()
        data.add_field("pipeline_id", pipeline_id)
        data.add_field("params", json.dumps(params), content_type="application/json")

        try:
            async with session.post(f"{LOCAL_SERVER_URL}key/api/v1/pipeline/run", data=data) as resp:
                result = await resp.json()
                job_id = result["uuid"]
        except aiohttp.ClientError as e:
            log_error(f"Ошибка при создании задачи генерации: {e}")
            raise RuntimeError(f"Не удалось создать задачу генерации: {e}")
        except KeyError as e:
            log_error(f"Неожиданный ответ от сервера генерации (run): {e}")
            raise RuntimeError(f"Сервер генерации вернул неожиданный ответ: {e}")

        # 3. Опрашиваем статус, пока картинка не будет готова
        poll_count = 0
        max_polls = 300  # 300 × 2 сек = 10 минут

        while True:
            poll_count += 1
            if poll_count > max_polls:
                raise RuntimeError(
                    f"Превышено время ожидания генерации ({max_polls * 2 // 60} минут). "
                    "Попробуйте упростить промпт или уменьшить размер изображения."
                )

            try:
                async with session.get(
                        f"{LOCAL_SERVER_URL}key/api/v1/pipeline/status/{job_id}"
                ) as resp:
                    status = await resp.json()
            except aiohttp.ClientError as e:
                log_error(f"Ошибка при проверке статуса генерации: {e}")
                raise RuntimeError(f"Потеряна связь с сервером генерации: {e}")

            if status["status"] == "DONE":
                return base64.b64decode(status["files"][0])
            if status["status"] == "FAIL":
                raise RuntimeError("Сервер вернул ошибку генерации")

            await asyncio.sleep(2)
