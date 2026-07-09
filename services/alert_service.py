# services/alert_service.py

"""
Фоновый сервис для проверки целей и отправки уведомлений.
"""

import asyncio
from database import get_active_alerts, deactivate_alert
from services.crypto_api import get_crypto_price
from logger import log_info, log_error


async def alert_checker(bot):
    """
    Бесконечный цикл проверки целей.
    Запускается из main как фоновая задача.
    """
    await asyncio.sleep(5)
    log_info("AlertChecker запущен")

    while True:
        await asyncio.sleep(60)  # Проверяем раз в минуту

        try:
            # Проходим по всем пользователям
            from database import users_db
            for user_id in list(users_db.keys()):
                alerts = get_active_alerts(user_id)
                if not alerts:
                    continue

                for alert in alerts:
                    coin = alert["coin"]
                    target = alert["target"]

                    price = get_crypto_price(coin)
                    if price is None:
                        continue

                    if price >= target:
                        try:
                            await bot.send_message(
                                user_id,
                                f"🚨 ВНИМАНИЕ! {coin.title()} достиг {target:.2f} USD!\n"
                                f"Текущий курс: {price:.2f} USD"
                            )
                            log_info(f"Уведомление отправлено пользователю {user_id} по {coin}")

                            # Деактивируем цель
                            alert_index = alerts.index(alert)
                            deactivate_alert(user_id, alert_index)

                        except Exception as e:
                            log_error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

        except Exception as e:
            log_error(f"Ошибка в alert_checker: {e}")