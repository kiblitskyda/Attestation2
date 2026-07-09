# services/fusionbrain_api.py

"""
Пример клиента: отправляет запрос на генерацию и сохраняет картинку.
Сервер должен быть уже запущен (python run_local.py).

"""
import base64
import json
import time

import requests

from config import LOCAL_SERVER_URL

BASE_URL = LOCAL_SERVER_URL  # используем настройку из config.py


def generate(prompt: str) -> bytes:
    # 1. Узнаём id доступного пайплайна.
    pipelines = requests.get(BASE_URL + "key/api/v1/pipelines").json()
    pipeline_id = pipelines[0]["id"]

    # 2. Ставим задачу на генерацию.
    params = {
        "type": "GENERATE",
        "numImages": 1,
        "width": 256,
        "height": 256,
        "generateParams": {"query": prompt},
    }
    response = requests.post(
        f"{BASE_URL}key/api/v1/pipeline/run",
        files={
            "pipeline_id": (None, pipeline_id),
            "params": (None, json.dumps(params), "application/json"),
        },
    ).json()
    print("Задача создана:", response)
    job_id = response["uuid"]

    # 3. Опрашиваем статус, пока картинка не будет готова.
    while True:
        status = requests.get(f"{BASE_URL}key/api/v1/pipeline/status/{job_id}").json()
        print("Статус:", status["status"])

        if status["status"] == "DONE":
            return base64.b64decode(status["files"][0])
        if status["status"] == "FAIL":
            raise RuntimeError("Сервер вернул ошибку генерации")
        time.sleep(2)


if __name__ == "__main__":
    image = generate("Незнайка на луне")
    with open("image.png", "wb") as f:
        f.write(image)
    print("Готово! Картинка сохранена в image.png")