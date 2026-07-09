#!/usr/bin/env python3
"""
Запуск локального сервера генерации изображений — без Docker.
Работает на macOS, Linux и Windows. Нужен только Python 3.10–3.12.

Самый простой способ — одна команда:

    python run_local.py

Скрипт сам подберёт сборку PyTorch под вашу видеокарту, поставит
зависимости в отдельное окружение .venv и запустит сервер на
http://localhost:8000

Если автоопределение ошиблось, устройство можно задать вручную:

    python run_local.py --device cpu     любая машина, без видеокарты
    python run_local.py --device cuda    видеокарта NVIDIA
    python run_local.py --device rocm    видеокарта AMD (только Linux)
    python run_local.py --device xpu     видеокарта Intel Arc (экспериментально)

Прочее:
    python run_local.py --port 8001      другой порт
    python run_local.py --skip-install   не переустанавливать зависимости
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"

# Короткое человеческое название устройства — для понятных сообщений.
DEVICE_HELP = {
    "cpu": "процессор (работает везде, но медленнее)",
    "cuda": "видеокарта NVIDIA",
    "rocm": "видеокарта AMD",
    "xpu": "видеокарта Intel",
    "mps": "видеокарта Apple (Metal)",
}

# PyTorch распространяется отдельными сборками под разное железо. Команда
# pip отличается только адресом репозитория (--index-url): по нему скачивается
# версия, скомпилированная именно под вашу видеокарту. Здесь — этот выбор.
TORCH_INSTALL = {
    "cpu": ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"],
    "cuda": ["torch", "--index-url", "https://download.pytorch.org/whl/cu121"],
    "rocm": ["torch", "--index-url", "https://download.pytorch.org/whl/rocm6.1"],
    "xpu": [
        "torch", "intel-extension-for-pytorch",
        "--extra-index-url",
        "https://pytorch-extension.intel.com/release-whl/stable/xpu/us/",
    ],
    # На macOS обычная сборка с PyPI уже умеет Apple Metal (MPS).
    "mps": ["torch"],
}


def venv_python() -> str:
    """Путь к python внутри .venv (на Windows он лежит в Scripts)."""
    if os.name == "nt":
        return str(VENV / "Scripts" / "python.exe")
    return str(VENV / "bin" / "python")


def detect_device() -> str:
    """
    Угадываем железо ещё до установки torch.

    - macOS  -> Apple Metal (MPS);
    - есть утилита nvidia-smi -> видеокарта NVIDIA;
    - иначе  -> процессор.

    AMD (rocm) и Intel (xpu) надёжно определить заранее нельзя — их
    задают вручную флагом --device.
    """
    if platform.system() == "Darwin":
        return "mps"
    if shutil.which("nvidia-smi"):
        return "cuda"
    return "cpu"


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Запуск локального сервера без Docker")
    parser.add_argument(
        "--device", default="auto",
        choices=["auto", "cpu", "cuda", "rocm", "xpu", "mps"],
        help="устройство для генерации (по умолчанию определяется автоматически)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default="8000")
    parser.add_argument("--skip-install", action="store_true",
                        help="пропустить установку зависимостей")
    args = parser.parse_args()

    device = detect_device() if args.device == "auto" else args.device
    print(f"\nВаша система: {platform.system()}")
    print(f"Генерировать буду на: {device} — {DEVICE_HELP[device]}\n")

    # Изолированное окружение, чтобы не засорять системный Python.
    if not VENV.exists():
        print("Создаю окружение .venv (это разовая операция)…")
        run([sys.executable, "-m", "venv", str(VENV)])

    py = venv_python()

    if not args.skip_install:
        run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        print(f"Качаю PyTorch под {device}. Это самая объёмная загрузка — можно заварить чай ☕")
        run([py, "-m", "pip", "install", *TORCH_INSTALL[device]])
        print("Ставлю остальные библиотеки (FastAPI, diffusers, …)…")
        run([py, "-m", "pip", "install", "--quiet", "-r", str(ROOT / "requirements-server.txt")])

    print(f"\nПоднимаю сервер: http://localhost:{args.port}")
    print("При первом запуске скачается модель bk-sdm-small (~0.5 ГБ) — подождите минуту.")
    print("Остановить: Ctrl+C\n")
    run([
        py, "-m", "uvicorn", "local_server:app",
        "--host", args.host, "--port", str(args.port),
    ])


if __name__ == "__main__":
    main()
