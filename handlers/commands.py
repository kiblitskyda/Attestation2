# handlers/commands.py

"""
Обработчики команд: /start, /help, /clean
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database import clear_context
from logger import log_info

router = Router()


@router.message(Command("start"))
async def handle_start(message: Message):
    """Приветствие и инструкция по использованию бота."""
    user_name = message.from_user.first_name or "пользователь"
    await message.answer(
        f"👋 Привет, {user_name}!\n\n"
        f"Я — мультимодальный бот. Я умею:\n"
        f"• Отвечать на текстовые вопросы\n"
        f"• Генерировать изображения по запросу\n\n"
        f"Просто напиши мне что-нибудь, и я отвечу!\n"
        f"Например:\n"
        f"• 'Расскажи про космос'\n"
        f"• 'Нарисуй закат на море'\n"
        f"• 'Расскажи про Париж и покажи Эйфелеву башню'\n\n"
        f"Команды:\n"
        f"/help — показать справку\n"
        f"/clean — очистить историю диалога"
    )
    log_info(f"Пользователь {message.from_user.id} запустил бота")


@router.message(Command("help"))
async def handle_help(message: Message):
    """Показывает справку."""
    await message.answer(
        "📖 **Справка по использованию бота**\n\n"
        "Я умею отвечать на текстовые вопросы и генерировать изображения.\n\n"
        "**Примеры запросов:**\n"
        "• 'Привет, как дела?' — обычный диалог\n"
        "• 'Нарисуй кота' — генерация изображения\n"
        "• 'Расскажи про динозавров и покажи тираннозавра' — текст + картинка\n\n"
        "**Команды:**\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/clean — очистить историю диалога\n\n"
        "**Важно:** Я запоминаю историю диалога, чтобы отвечать связно. "
        "Если хотите начать новую тему — используйте /clean."
    )


@router.message(Command("clean"))
async def handle_clean(message: Message):
    """Очищает историю диалога пользователя."""
    user_id = message.from_user.id
    clear_context(user_id)
    await message.answer("🧹 История диалога очищена! Можно начинать новую тему.")
    log_info(f"Пользователь {user_id} очистил контекст")