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


## Краткое описание файлов:

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


Схема работы бота

Схема 1: Полный маршрут сообщения (общая картина)

ПОЛЬЗОВАТЕЛЬ
    │
    ▼
1. Telegram → [main.py] → диспетчер (dp)
    │
    ▼
2. [middlewares/ratelimit.py] → проверка спама (если часто — отсекаем)
    │
    ▼
3. [handlers/multimodal.py] → главный хендлер (ловит все сообщения, кроме команд)
    │
    ├─ проверка: "пользователь в опросе?" → если да → сообщаем и выходим
    │
    ├─ проверка лимита запросов (check_rate_limit)
    │
    ▼
4. [services/classifier.py] → определяем НАМЕРЕНИЕ
    │
    ├─ "currency" → передаём в [handlers/currency.py] → ответ сразу
    ├─ "crypto"   → передаём в [handlers/currency.py] → ответ сразу
    ├─ "generate" → идём дальше
    └─ "other"    → идём дальше
    │
    ▼
5. [services/dialog_service.py] → отправляем запрос в YandexGPT
    │
    ├─ добавляем системный промпт (с данными poll_data)
    ├─ добавляем историю диалога
    ├─ отправляем → получаем JSON-массив:
    │     [{"text": "..."}, {"image": "..."}]
    │
    ▼
6. [handlers/multimodal.py] → чистим JSON, парсим в список задач
    │
    ▼
7. [services/chain.py] → запускаем ЦЕПОЧКУ ОБЯЗАННОСТЕЙ
    │
    ├─ TextExecutor → видит {"text": ...} → отправляет мгновенно
    ├─ ImageExecutor → видит {"image": ...} → ставит в очередь
    │
    ▼
8. [services/queue.py] → ОЧЕРЕДЬ (воркеры в фоне)
    │
    ├─ Воркер забирает задачу
    ├─ вызывает [services/api/fusionbrain_api.py] → генерирует картинку
    ├─ отправляет результат пользователю
    │
    ▼
ПОЛЬЗОВАТЕЛЬ (получает ответ)


Схема 2: Пример 1 — пользователь пишет «привет»
Шаг	Что происходит	Кто решает
1	Привет → Telegram → main.py	Диспетчер
2	Проверка спама	ratelimit.py
3	Сообщение попадает в multimodal.py	Хендлер
4	Классификатор: «other»	classifier.py
5	Отправляем в YandexGPT → получаем [{"text": "Здравствуйте!"}]	dialog_service.py
6	Чистим JSON → список задач	multimodal.py
7	Цепочка: TextExecutor видит {"text": ...} → отправляет	chain.py
8	Пользователь получает ответ	—
Итог: Текст → мгновенно. Очередь не используется.

Схема 3: Пример 2 — пользователь пишет «нарисуй корабль»
Шаг	Что происходит	Кто решает
1	Корабль → Telegram → main.py	Диспетчер
2	Проверка спама	ratelimit.py
3	Сообщение попадает в multimodal.py	Хендлер
4	Классификатор: «generate»	classifier.py
5	Отправляем в YandexGPT → получаем [{"image": "ship at sea..."}]	dialog_service.py
6	Чистим JSON → список задач	multimodal.py
7	Цепочка: TextExecutor → не видит текста → передаёт дальше	chain.py
8	ImageExecutor видит {"image": ...} → ставит в очередь	chain.py
9	Бот сразу отвечает: «Картинка в очереди»	chain.py
10	Воркер забирает задачу → генерирует → отправляет	queue.py + fusionbrain_api.py
11	Пользователь получает картинку	—
Итог: Бот ответил мгновенно → картинка пришла отдельно через 3 минуты.

Схема 4: Пример 3 — пользователь пишет «курс доллара»
Шаг	Что происходит	Кто решает
1	Курс доллара → Telegram → main.py	Диспетчер
2	Проверка спама	ratelimit.py
3	Сообщение попадает в multimodal.py	Хендлер
4	Классификатор: «currency»	classifier.py
5	Маршрутизация: intent == "currency" → передаём в handlers/currency.py	multimodal.py
6	currency.py → курс доллара → ответ	currency_api.py
7	Пользователь получает ответ	—
Итог: Ни YandexGPT, ни цепочка, ни очередь не вызываются. Всё мгновенно.