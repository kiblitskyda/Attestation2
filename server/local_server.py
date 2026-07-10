#server/local_server

import asyncio
import base64
import json
import logging
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from io import BytesIO
from typing import Any, Optional

import torch

try:
    # Подключаем поддержку видеокарт Intel (XPU). Если библиотека не
    # установлена — просто работаем без неё, ошибки нет.
    import intel_extension_for_pytorch as ipex  # noqa: F401
except ImportError:
    pass

from diffusers import DiffusionPipeline
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    INITIAL = "INITIAL"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAIL = "FAIL"


# Хранилище задач в памяти: job_id -> состояние генерации.
jobs: dict[str, dict[str, Any]] = {}
pipeline: Optional[DiffusionPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загружаем модель один раз при старте сервера и держим в памяти."""
    global pipeline
    logger.info("Загружаю модель nota-ai/bk-sdm-small…")

    # Выбираем самое быстрое доступное устройство. Порядок важен: сначала
    # дискретные видеокарты, потом Apple Metal, потом Intel, и лишь затем CPU.
    if torch.cuda.is_available():
        # Один и тот же код покрывает NVIDIA (CUDA) и AMD (ROCm) —
        # в PyTorch видеокарта AMD тоже видна как "cuda".
        device, dtype = "cuda", torch.float16
        logger.info("Использую видеокарту (NVIDIA CUDA / AMD ROCm)")
    elif torch.backends.mps.is_available():
        device, dtype = "mps", torch.float32
        logger.info("Использую видеокарту Apple (Metal)")
    elif hasattr(torch, "xpu") and torch.xpu.is_available():
        device, dtype = "xpu", torch.float16
        logger.info("Использую видеокарту Intel (XPU)")
    else:
        device, dtype = "cpu", torch.float32
        logger.info("Использую процессор (CPU)")

    pipeline = DiffusionPipeline.from_pretrained(
        "nota-ai/bk-sdm-small",
        torch_dtype=dtype,
        # Выключаем фильтр контента — для учебного демо он лишний и только
        # замедляет загрузку.
        safety_checker=None,
        requires_safety_checker=False,
    ).to(device)

    # Экономит видеопамять ценой небольшой потери скорости — помогает на
    # слабых картах и ноутбуках.
    pipeline.enable_attention_slicing()

    logger.info(f"Модель готова, устройство: {device}")
    yield
    pipeline = None
    logger.info("Сервер остановлен, модель выгружена")


app = FastAPI(
    title="Local Image Generation API (FusionBrain-compatible)",
    lifespan=lifespan,
)


@app.get("/key/api/v1/pipelines")
async def get_pipelines():
    """Список доступных пайплайнов — повторяет формат ответа FusionBrain."""
    return [
        {"id": "1", "name": "BK-SDM-Small (local)", "version": "1.0", "type": "TEXT2IMAGE"}
    ]


@app.post("/key/api/v1/pipeline/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    pipeline_id: str = Form(...),
    params: str = Form(...),
):
    """
    Принимаем запрос на генерацию и сразу отдаём job_id, а саму картинку
    считаем в фоне — клиент потом опрашивает статус по этому id.

    Поле params — это JSON-строка, например:
        {
          "type": "GENERATE",
          "numImages": 1,
          "width": 512,
          "height": 512,
          "generateParams": {"query": "cyberpunk city at night, neon, rain"}
        }
    """
    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="params must be valid JSON")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": JobStatus.INITIAL, "files": []}

    background_tasks.add_task(_generate_image_task, job_id=job_id, params=params_dict)

    logger.info(f"Создана задача {job_id}")
    return {"uuid": job_id, "status": JobStatus.INITIAL}


@app.get("/key/api/v1/pipeline/status/{job_uuid}")
async def get_status(job_uuid: str):
    """Статус задачи. Когда готово — отдаём картинки и удаляем задачу из памяти."""
    if job_uuid not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_uuid]

    if job["status"] == JobStatus.DONE:
        result = {"uuid": job_uuid, "status": JobStatus.DONE, "files": job["files"]}
        del jobs[job_uuid]
        return result

    return {"uuid": job_uuid, "status": job["status"], "files": []}


async def _generate_image_task(job_id: str, params: dict):
    """Фоновая задача: считает картинку и складывает результат в jobs[job_id]."""
    jobs[job_id]["status"] = JobStatus.PROCESSING
    logger.info(f"[{job_id}] начинаю генерацию…")

    try:
        query = params.get("generateParams", {}).get("query", "")
        width = params.get("width", 512)
        height = params.get("height", 512)
        num_images = params.get("numImages", 1)

        # Генерация блокирующая, поэтому выносим её в отдельный поток,
        # чтобы сервер продолжал отвечать на другие запросы.
        images = await asyncio.to_thread(
            _run_pipeline, prompt=query, width=width, height=height, num_images=num_images
        )

        # Картинки отдаём строками base64 — так их удобно класть в JSON.
        files_b64 = []
        for img in images:
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            files_b64.append(base64.b64encode(buffer.getvalue()).decode("utf-8"))

        jobs[job_id]["files"] = files_b64
        jobs[job_id]["status"] = JobStatus.DONE
        logger.info(f"[{job_id}] готово")

    except Exception as e:
        logger.error(f"[{job_id}] ошибка: {e}")
        jobs[job_id]["status"] = JobStatus.FAIL
        jobs[job_id]["error"] = str(e)


def _run_pipeline(prompt: str, width: int, height: int, num_images: int) -> list[Image.Image]:
    # Модель обучена на 512x512, поэтому больший размер не запрашиваем.
    result = pipeline(
        prompt=prompt,
        width=min(width, 512),
        height=min(height, 512),
        num_images_per_prompt=num_images,
        num_inference_steps=20,
        guidance_scale=7.5,
    )
    return result.images


@app.get("/health")
async def health():
    """Проверка, что сервер жив и модель загружена."""
    return {"status": "ok", "model_loaded": pipeline is not None, "active_jobs": len(jobs)}

