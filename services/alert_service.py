# services/alert_service.py

"""
Фоновый сервис для проверки целей и отправки уведомлений.
"""

import asyncio
from database import get_active_alerts, get_all_user_ids, deactivate_alerts_by_params
from services.crypto_api import get_crypto_price
from services.currency_api import get_exchange_rate
from logger import log_function_call, log_info, log_error


@log_function_call
async def alert_checker(bot, stop_event: asyncio.Event):
    """
    Бесконечный цикл проверки целей для валют и криптовалют.
    Останавливается при установке stop_event.
    """
    await asyncio.sleep(5)
    log_info("AlertChecker запущен")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
            break
        except asyncio.TimeoutError:
            pass

        try:
            for user_id in get_all_user_ids():
                alerts = get_active_alerts(user_id)
                if not alerts:
                    continue

                for alert in alerts:
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
                                await deactivate_alerts_by_params(
                                    user_id, "currency", item, target
                                )

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
                            await deactivate_alerts_by_params(
                                user_id, "crypto", item, target
                            )

                            await bot.send_message(
                                user_id,
                                f"🚨 ВНИМАНИЕ! {item.title()} достиг {target:.2f} USD!\n"
                                f"Текущий курс: {price:.2f} USD"
                            )
                            log_info(f"Уведомление по криптовалюте отправлено пользователю {user_id}")

        except Exception as e:
            log_error(f"Ошибка в alert_checker: {e}")

    log_info("AlertChecker остановлен")