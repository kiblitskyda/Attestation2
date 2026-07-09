# fusionbrain_api.py
import base64
import json
import time
import requests
from typing import List


class FusionBrainAPI:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/"):
        self.base_url = base_url

    def get_pipeline_id(self) -> str:
        response = requests.get(self.base_url + "key/api/v1/pipelines")
        pipelines = response.json()
        return pipelines[0]["id"]

    # Метод, который будем декорировать
    async def generate_images(self, prompt: str, num_images: int = 2, width: int = 256, height: int = 256) -> List[
        bytes]:
        """
        Генерирует изображения по текстовому описанию.
        Возвращает список байтов (каждое изображение).
        """
        pipeline_id = self.get_pipeline_id()

        params = {
            "type": "GENERATE",
            "numImages": num_images,
            "width": width,
            "height": height,
            "generateParams": {"query": prompt},
        }

        response = requests.post(
            f"{self.base_url}key/api/v1/pipeline/run",
            files={
                "pipeline_id": (None, pipeline_id),
                "params": (None, json.dumps(params), "application/json"),
            },
        )
        job_id = response.json()["uuid"]

        while True:
            status_response = requests.get(f"{self.base_url}key/api/v1/pipeline/status/{job_id}")
            status_data = status_response.json()

            if status_data["status"] == "DONE":
                images = []
                for file_b64 in status_data["files"]:
                    images.append(base64.b64decode(file_b64))
                return images

            if status_data["status"] == "FAIL":
                raise RuntimeError("Ошибка генерации изображения")

            time.sleep(2)