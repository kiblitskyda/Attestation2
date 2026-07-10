# handlers/commands.py

"""
Обработчики команд: /start, /help, /clean, /stats, /alerts
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import clear_context, get_context, get_active_alerts
from logger import log_info, log_handler
import pandas as pd

router = Router()


@router.message(Command("start"))
@log_handler
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
        f"/poll — пройти анкету\n"
        f"/help — показать справку\n"
        f"/clean — очистить историю диалога"
    )
    log_info(f"Пользователь {message.from_user.id} запустил бота")


@router.message(Command("help"))
@log_handler
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
        "/clean — очистить историю диалога\n"
        "/stats — статистика по диалогам\n"
        "/alerts — список активных целей\n\n"
        "**Важно:** Я запоминаю историю диалога, чтобы отвечать связно. "
        "Если хотите начать новую тему — используйте /clean."
    )


@router.message(Command("clean"))
@log_handler
async def handle_clean(message: Message):
    """Очищает историю диалога пользователя."""
    user_id = message.from_user.id
    clear_context(user_id)
    await message.answer("🧹 История диалога очищена! Можно начинать новую тему.")
    log_info(f"Пользователь {user_id} очистил контекст")


@router.message(Command("stats"))
@log_handler
async def handle_stats(message: Message):
    """
    Показывает статистику по диалогам пользователя.
    """
    user_id = message.from_user.id
    context = list(get_context(user_id))

    if not context:
        await message.answer("📭 Нет данных для статистики. Напишите что-нибудь боту.")
        return

    # Преобразуем данные в DataFrame
    data = []
    for msg in context:
        text = msg.get("text", "")
        data.append({
            "role": msg.get("role"),
            "length": len(text),
            "words": len(text.split())
        })

    df = pd.DataFrame(data)

    total = len(df)
    user_msgs = len(df[df["role"] == "user"])
    bot_msgs = len(df[df["role"] == "assistant"])
    avg_len = df["length"].mean()
    max_len = df["length"].max()
    min_len = df["length"].min()
    total_words = df["words"].sum()
    avg_words = df["words"].mean()

    await message.answer(
        f"📊 **Ваша статистика**\n\n"
        f"Всего сообщений: {total}\n"
        f"  • Ваших: {user_msgs}\n"
        f"  • Ответов бота: {bot_msgs}\n\n"
        f"📝 Длина сообщений:\n"
        f"  • Средняя: {avg_len:.1f} символов\n"
        f"  • Самое длинное: {max_len}\n"
        f"  • Самое короткое: {min_len}\n\n"
        f"🔤 Слова:\n"
        f"  • Всего слов: {total_words}\n"
        f"  • В среднем: {avg_words:.1f} слов/сообщение"
    )
    log_info(f"Пользователь {user_id} запросил статистику")


@router.message(Command("alerts"))
@log_handler
async def handle_alerts(message: Message):
    """
    Показывает все активные цели пользователя (валюты и криптовалюты).
    """
    user_id = message.from_user.id
    alerts = get_active_alerts(user_id)

    if not alerts:
        await message.answer(
            "📭 У вас нет активных целей. Чтобы установить цель, скажите:\n"
            "• 'следить за биткоином'\n"
            "• 'следить за долларом'"
        )
        return

    # Преобразуем данные в DataFrame
    data = []
    for alert in alerts:
        alert_type = alert.get("type", "crypto")
        item = alert.get("item", alert.get("coin", "—"))
        target = alert.get("target", 0)

        if alert_type == "currency":
            type_label = "💰 Валюта"
        else:
            type_label = "🪙 Криптовалюта"
            item = item.title()  # bitcoin → Bitcoin

        data.append({
            "Тип": type_label,
            "Инструмент": item,
            "Цель": f"{target:.2f}"
        })

    df = pd.DataFrame(data)

    # Если целей больше 10, показываем только первые 10
    display_df = df.head(10)
    table = display_df.to_string(index=False)

    header = f"📊 **Ваши активные цели ({len(alerts)})**\n\n"
    if len(alerts) > 10:
        header += f"*(показаны первые 10 из {len(alerts)})*\n\n"

    await message.answer(
        f"{header}"
        f"<pre>{table}</pre>",
        parse_mode="HTML"
    )

    log_info(f"Пользователь {user_id} запросил список целей")

