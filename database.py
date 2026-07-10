#database.py

"""
Модуль для работы с базой данных бота.

Использует In-Memory хранилище с сохранением в JSON-файл.
Данные о пользователях хранятся в виде объектов User.
"""

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config import DB_FILE, MAX_CONTEXT_MESSAGES, RATE_LIMIT_MESSAGES_PER_HOUR
from logger import log_function_call, log_info, log_error, log_warning
from models.user import User


# Основное хранилище данных в памяти
users_db: Dict[int, User] = {}

# Отдельное хранилище для лимитов запросов
rate_limit_db: Dict[int, Dict[str, Any]] = {}

# Блокировки для потокобезопасной работы с пользователями
_user_locks: Dict[int, asyncio.Lock] = {}


def _get_user_lock(user_id: int) -> asyncio.Lock:
    """Возвращает блокировку для пользователя (создаёт при необходимости)."""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


# --- ЗАГРУЗКА И СОХРАНЕНИЕ ---

@log_function_call
def load_db():
    """Загружает базу данных из JSON-файла."""
    global users_db, rate_limit_db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

            # Загружаем пользователей
            users_db = {
                int(user_id): User.from_dict(user_data)
                for user_id, user_data in raw_data.get("users", {}).items()
            }

            # Загружаем лимиты, приводя ключи к int
            raw_limits = raw_data.get("rate_limits", {})
            rate_limit_db = {}
            for user_id, data in raw_limits.items():
                uid = int(user_id)
                # Если ключ уже есть — оставляем запись с более свежим last_request
                if uid in rate_limit_db:
                    existing_time = rate_limit_db[uid].get("last_request", "")
                    new_time = data.get("last_request", "")
                    if new_time > existing_time:
                        rate_limit_db[uid] = data
                else:
                    rate_limit_db[uid] = data

    except FileNotFoundError:
        users_db = {}
        rate_limit_db = {}
    except json.JSONDecodeError:
        users_db = {}
        rate_limit_db = {}


@log_function_call
def save_db():
    """Сохраняет базу данных в JSON-файл."""
    # Убеждаемся, что все ключи в rate_limit_db — int (защита от багов)
    clean_limits = {}
    for user_id, data in rate_limit_db.items():
        clean_limits[str(user_id)] = data

    db_to_save = {
        "users": {str(user_id): user.to_dict() for user_id, user in users_db.items()},
        "rate_limits": clean_limits,
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
def get_all_user_ids() -> list[int]:
    """Возвращает список всех ID пользователей в базе."""
    return list(users_db.keys())


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

@log_function_call
async def add_alert(user_id: int, item: str, target: float, alert_type: str = "crypto") -> bool:
    """
    Добавляет цель для уведомления (валюты или криптовалюты).
    Потокобезопасна за счёт asyncio.Lock.
    Не добавляет дубликат, если точно такая же активная цель уже существует.

    Args:
        user_id: ID пользователя
        item: Код валюты ("USD/RUB") или криптовалюты ("bitcoin")
        target: Целевая цена
        alert_type: "currency" или "crypto"

    Returns:
        True, если цель добавлена, False если дубликат
    """
    lock = _get_user_lock(user_id)
    async with lock:
        user = get_user(user_id)

        # Проверка на дубликат
        for alert in user.alerts:
            if (alert.get("active") and
                alert.get("type") == alert_type and
                alert.get("item") == item and
                alert.get("target") == target):
                log_info(f"Дубликат цели для {user_id}: {item} = {target} ({alert_type}) — не добавлен")
                return False

        user.alerts.append({
            "type": alert_type,
            "item": item,
            "target": target,
            "active": True
        })
        save_db()
        log_info(f"Добавлена цель для {user_id}: {item} = {target} ({alert_type})")
        return True


@log_function_call
def get_active_alerts(user_id: int) -> List[Dict[str, Any]]:
    """Возвращает список активных целей пользователя."""
    user = get_user(user_id)
    return [alert for alert in user.alerts if alert.get("active", True)]


@log_function_call
async def deactivate_alert(user_id: int, alert_index: int):
    """Деактивирует цель по индексу. Потокобезопасна."""
    lock = _get_user_lock(user_id)
    async with lock:
        user = get_user(user_id)
        if 0 <= alert_index < len(user.alerts):
            user.alerts[alert_index]["active"] = False
            save_db()
            log_info(f"Деактивирована цель для {user_id}: индекс {alert_index}")
        else:
            log_warning(f"Попытка деактивировать несуществующую цель {alert_index} для {user_id}")


@log_function_call
async def deactivate_alerts_by_params(user_id: int, alert_type: str, item: str, target: float) -> int:
    """
    Деактивирует все активные цели с указанными параметрами.
    Потокобезопасна. Возвращает количество деактивированных целей.
    """
    lock = _get_user_lock(user_id)
    async with lock:
        user = get_user(user_id)
        count = 0
        for i, a in enumerate(user.alerts):
            if (a.get("active") and
                a.get("type") == alert_type and
                a.get("item") == item and
                a.get("target") == target):
                user.alerts[i]["active"] = False
                count += 1
        if count > 0:
            save_db()
            log_info(f"Деактивировано {count} целей для {user_id}: {item} = {target}")
        return count