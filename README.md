#README.md

# Мультимодальный Telegram-бот

Учебный проект. Бот отвечает на вопросы, генерирует изображения, отслеживает курсы валют и криптовалют.

## Возможности

- Текстовые ответы (YandexGPT)
- Генерация изображений (локальный сервер, модель bk-sdm-small)
- Курсы валют (freecurrencyapi) и криптовалют (CoinGecko)
- Установка ценовых целей с уведомлениями
- Опросы через FSM

## Установка

1. Клонировать репозиторий
2. Установить зависимости: `pip install -r requirements.txt`
3. Создать `.env` с ключами (см. `.env.example`)
4. Запустить сервер генерации: `python server/run_local.py --device cpu`
5. Запустить бота: `python main.py`

## Структура проекта

- `handlers/` — обработчики сообщений
- `services/` — бизнес-логика
- `models/` — модели данных
- `middlewares/` — middleware
- `server/` — локальный сервер генерации изображений
-

1. models/user.py          → что такое пользователь
2. database.py              → как хранить пользователей
3. config.py + core.py      → откуда берутся настройки и кто создаёт бота
4. logger.py                → как логировать

5. services/classifier.py   → как понимать, чего хочет пользователь
6. services/dialog_service.py → как общаться с YandexGPT

7. services/chain.py        → как обрабатывать задачи (текст/картинка)
8. services/queue.py        → как делать картинки в фоне
9. services/api/fusionbrain_api.py → как генерировать картинки

10. services/api/crypto_api.py + currency_api.py → курсы валют

11. states/poll.py + states/currency.py → состояния для FSM
12. handlers/poll.py + handlers/currency.py → обработка опроса и целей

13. handlers/multimodal.py  → главный маршрутизатор запросов
14. handlers/commands.py    → команды /start, /help, /stats, /alerts

15. middlewares/ratelimit.py → защита от спама
16. services/alert_service.py → фоновые уведомления

17. main.py → точка входа