# services/alert_service.py

"""
Фоновый сервис для проверки целей и отправки уведомлений.
"""

import asyncio
from database import get_active_alerts, get_user, save_db
from services.crypto_api import get_crypto_price
from services.currency_api import get_exchange_rate
from logger import log_info, log_error


async def alert_checker(bot):
    """
    Бесконечный цикл проверки целей для валют и криптовалют.
    """
    await asyncio.sleep(5)
    log_info("AlertChecker запущен")

    while True:
        await asyncio.sleep(60)

        try:
            from database import users_db
            for user_id in list(users_db.keys()):
                alerts = get_active_alerts(user_id)
                if not alerts:
                    continue

                for alert in alerts:
                    # Проверяем, что цель всё ещё активна
                    if not alert.get("active"):
                        continue

                    alert_type = alert.get("type", "crypto")
                    item = alert["item"]
                    target = alert["target"]

                    if alert_type == "currency":
                        base, target_currency = item.split("/")
                        try:
                            current_rate = get_exchange_rate(base, target_currency)
                            if current_rate and current_rate >= target:
                                # Деактивируем ВСЕ цели с такими же параметрами
                                user = get_user(user_id)
                                for i, a in enumerate(user.alerts):
                                    if (a.get("active") and
                                        a.get("type") == "currency" and
                                        a.get("item") == item and
                                        a.get("target") == target):
                                        user.alerts[i]["active"] = False
                                save_db()

                                await bot.send_message(
                                    user_id,
                                    f"🚨 ВНИМАНИЕ! Курс {base} к {target_currency} достиг {target:.2f}!\n"
                                    f"Текущий курс: 1 {base} = {current_rate:.2f} {target_currency}"
                                )
                                log_info(f"Уведомление по валюте отправлено пользователю {user_id}")
                        except Exception as e:
                            log_error(f"Ошибка проверки курса валюты {item}: {e}")

                    else:  # crypto
                        price = get_crypto_price(item)
                        if price and price >= target:
                            # Деактивируем ВСЕ цели с такими же параметрами
                            user = get_user(user_id)
                            for i, a in enumerate(user.alerts):
                                if (a.get("active") and
                                    a.get("type") == "crypto" and
                                    a.get("item") == item and
                                    a.get("target") == target):
                                    user.alerts[i]["active"] = False
                            save_db()

                            await bot.send_message(
                                user_id,
                                f"🚨 ВНИМАНИЕ! {item.title()} достиг {target:.2f} USD!\n"
                                f"Текущий курс: {price:.2f} USD"
                            )
                            log_info(f"Уведомление по криптовалюте отправлено пользователю {user_id}")

        except Exception as e:
            log_error(f"Ошибка в alert_checker: {e}")