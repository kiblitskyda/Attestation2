# models/user.py

"""
Модель пользователя.
Описывает структуру данных, которые мы храним о пользователе.
"""

from collections import deque
from typing import List, Dict, Any, Optional

from config import MAX_CONTEXT_MESSAGES, DEFAULT_SYSTEM_PROMPT


class User:
    """
    Класс, описывающий пользователя бота.

    Атрибуты:
        system_prompt (str): Системный промпт (роль ассистента)
        context (deque): История диалога
        role (str): Роль пользователя (всегда "user")
        alerts (List[Dict[str, Any]]): Список целей для уведомлений
        poll_data (Dict[str, Any]): Данные из опроса (имя, возраст, город, деятельность)
    """

    def __init__(
        self,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        context: Optional[deque] = None,
        role: str = "user",
        alerts: Optional[List[Dict[str, Any]]] = None,
        poll_data: Optional[Dict[str, Any]] = None,
    ):
        self.system_prompt = system_prompt
        self.context = context if context is not None else deque(maxlen=MAX_CONTEXT_MESSAGES)
        self.role = role
        self.alerts = alerts if alerts is not None else []
        self.poll_data = poll_data if poll_data is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        """Превращает объект User в словарь для сохранения в JSON."""
        return {
            "system_prompt": self.system_prompt,
            "context": list(self.context),
            "role": self.role,
            "alerts": self.alerts,
            "poll_data": self.poll_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Восстанавливает объект User из словаря (при загрузке из JSON)."""
        return cls(
            system_prompt=data.get("system_prompt", DEFAULT_SYSTEM_PROMPT),
            context=deque(data.get("context", []), maxlen=MAX_CONTEXT_MESSAGES),
            role=data.get("role", "user"),
            alerts=data.get("alerts", []),
            poll_data=data.get("poll_data", {}),
        )