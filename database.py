#database.py

"""
Модуль для работы с базой данных бота.

Использует In-Memory хранилище с сохранением в JSON-файл.
Данные о пользователях хранятся в виде объектов User.
"""

import json
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config import DB_FILE, MAX_CONTEXT_MESSAGES, RATE_LIMIT_MESSAGES_PER_HOUR
from logger import log_function_call
from models.user import User
from logger import log_info, log_error, log_warning



# Основное хранилище данных в памяти
users_db: Dict[int, User] = {}

# Отдельное хранилище для лимитов запросов
rate_limit_db: Dict[int, Dict[str, Any]] = {}


# --- ЗАГРУЗКА И СОХРАНЕНИЕ ---

@log_function_call
def load_db():
    """Загружает базу данных из JSON-файла."""
    global users_db, rate_limit_db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            users_db = {
                int(user_id): User.from_dict(user_data)
                for user_id, user_data in raw_data.get("users", {}).items()
            }
            rate_limit_db = raw_data.get("rate_limits", {})
    except FileNotFoundError:
        users_db = {}
        rate_limit_db = {}
    except json.JSONDecodeError:
        users_db = {}
        rate_limit_db = {}


@log_function_call
def save_db():
    """Сохраняет базу данных в JSON-файл."""
    db_to_save = {
        "users": {str(user_id): user.to_dict() for user_id, user in users_db.items()},
        "rate_limits": rate_limit_db,
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_to_save, f, ensure_ascii=False, indent=2)


# --- РАБОТА С ПОЛЬЗОВАТЕЛЕМ ---

@log_function_call
def get_user(user_id: int) -> User:
    """Возвращает объект User. Если пользователя нет — создаёт нового."""
    if user_id not in users_db:
        users_db[user_id] = User()
        save_db()
    return users_db[user_id]


@log_function_call
def get_context(user_id: int) -> deque:
    """Возвращает контекст пользователя (историю диалога)."""
    return get_user(user_id).context


@log_function_call
def get_full_context(user_id: int) -> List[Dict[str, str]]:
    """Возвращает полный контекст для отправки в модель: system + диалог."""
    user = get_user(user_id)
    context = list(user.context)
    context.insert(0, {"role": "system", "text": user.system_prompt})
    return context


@log_function_call
def clear_context(user_id: int):
    """Очищает контекст, сохраняя system-промпт."""
    user = get_user(user_id)
    user.context.clear()
    save_db()


@log_function_call
def add_to_context(user_id: int, new_message: Dict[str, str]):
    """Добавляет сообщение в контекст."""
    user = get_user(user_id)
    user.context.append(new_message)
    save_db()


@log_function_call
def set_system_prompt(user_id: int, prompt: str):
    """Устанавливает новый system-промпт."""
    user = get_user(user_id)
    user.system_prompt = prompt
    save_db()


# --- ОГРАНИЧЕНИЯ ---

@log_function_call
def check_rate_limit(user_id: int) -> bool:
    """
    Проверяет, не превысил ли пользователь лимит запросов за час.
    Возвращает True, если можно отправлять запрос, иначе False.
    """
    now = datetime.now()
    limit = RATE_LIMIT_MESSAGES_PER_HOUR

    # Если пользователя нет в rate_limit_db — создаём запись
    if user_id not in rate_limit_db:
        rate_limit_db[user_id] = {
            "count": 0,
            "last_request": now.isoformat(),
        }
        save_db()
        return True

    user_limit = rate_limit_db[user_id]
    last = datetime.fromisoformat(user_limit["last_request"])

    # Если прошёл час — сбрасываем счётчик
    if now - last > timedelta(hours=1):
        user_limit["count"] = 0
        user_limit["last_request"] = now.isoformat()
        save_db()
        return True

    # Проверяем, не превышен ли лимит
    if user_limit["count"] >= limit:
        return False

    # Увеличиваем счётчик и обновляем время
    user_limit["count"] += 1
    user_limit["last_request"] = now.isoformat()
    save_db()
    return True

# --- ЦЕЛИ ДЛЯ УВЕДОМЛЕНИЙ ---

def add_alert(user_id: int, coin: str, target: float):
    """Добавляет цель для уведомления."""
    user = get_user(user_id)
    user.alerts.append({"coin": coin, "target": target, "active": True})
    save_db()
    log_info(f"Добавлена цель для {user_id}: {coin} = {target}")


def get_active_alerts(user_id: int) -> list:
    """Возвращает список активных целей пользователя."""
    user = get_user(user_id)
    return [alert for alert in user.alerts if alert.get("active", True)]


def deactivate_alert(user_id: int, alert_index: int):
    """Деактивирует цель."""
    user = get_user(user_id)
    if 0 <= alert_index < len(user.alerts):
        user.alerts[alert_index]["active"] = False
        save_db()
        log_info(f"Деактивирована цель для {user_id}: индекс {alert_index}")