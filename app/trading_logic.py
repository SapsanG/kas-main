# trading_logic.py

import asyncio
import logging
import math
import traceback
import time
from app.shared import bot_state_manager, get_user_context
from telegram import Update
import ccxt

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Исправление для начала функции start_trading

async def start_trading(symbol: str, update: Update) -> None:
    user_id = update.effective_user.id
    logger.info(f"========== НАЧАЛО АВТОТОРГОВЛИ ==========")
    logger.info(f"Автоторговля запущена для пользователя {user_id}, символ {symbol}")

    # Отправляем сообщение о начале процесса
    await update.message.reply_text(f"🔄 Запускаю автоторговлю для {symbol}...")

    # Сначала проверяем, не запущена ли уже торговля
    if bot_state_manager.is_trading_active(user_id):
        logger.warning(f"Автоторговля уже запущена для пользователя {user_id}")

        # Принудительно сбрасываем и перезапускаем
        logger.info(f"Сброс предыдущего состояния автоторговли")
        bot_state_manager.stop(user_id)
        await update.message.reply_text('Предыдущая сессия автоторговли была сброшена.')

    # Получаем контекст пользователя
    try:
        user_context = get_user_context(user_id)
        logger.info(f"Контекст пользователя получен успешно")
        await update.message.reply_text(f"✅ Контекст пользователя загружен")
    except Exception as e:
        logger.error(f"Ошибка при получении контекста пользователя: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении контекста пользователя: {str(e)}")
        return

    # Отмечаем, что торговля запущена
    bot_state_manager.start(user_id)
    logger.info(f"Статус торговли установлен в активный для пользователя {user_id}")
    await update.message.reply_text('✅ Автоторговля активирована. Чтобы остановить, используйте команду /stop.')

    # Логируем параметры пользователя
    logger.info(f"Параметры пользователя {user_id}:")
    logger.info(f"- Процент прибыли: {user_context.bot_params.profit_percentage}%")
    logger.info(f"- Процент падения: {user_context.bot_params.fall_percentage}%")
    logger.info(f"- Задержка: {user_context.bot_params.delay_seconds} сек")
    logger.info(f"- Размер ордера: {user_context.bot_params.order_size} USDT")

    await update.message.reply_text(
        f"📊 Текущие параметры:\n"
        f"- Процент прибыли: {user_context.bot_params.profit_percentage}%\n"
        f"- Процент падения: {user_context.bot_params.fall_percentage}%\n"
        f"- Задержка: {user_context.bot_params.delay_seconds} сек\n"
        f"- Размер ордера: {user_context.bot_params.order_size} USDT"
    )

    try:
        # Получаем экземпляр MEXC для пользователя
        logger.info(f"Попытка создания экземпляра MEXC для пользователя {user_id}")
        await update.message.reply_text("🔄 Подключение к MEXC...")

        try:
            mexc_instance = user_context.get_mexc_instance()
            logger.info(f"Экземпляр MEXC успешно создан")
            await update.message.reply_text("✅ Подключение к MEXC успешно")
        except Exception as e:
            logger.error(f"Ошибка при создании экземпляра MEXC: {e}")
            await update.message.reply_text(f"❌ Ошибка подключения к MEXC: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Проверяем баланс
        logger.info(f"Проверка баланса пользователя {user_id}")
        await update.message.reply_text("🔄 Проверка баланса...")

        try:
            balance = mexc_instance.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            logger.info(f"Баланс USDT пользователя {user_id}: {usdt_balance}")
            await update.message.reply_text(f"💰 Доступный баланс: {usdt_balance} USDT")

            # Проверяем, достаточно ли средств
            if usdt_balance < user_context.bot_params.order_size:
                logger.warning(f"Недостаточно средств для пользователя {user_id}. "
                               f"Баланс: {usdt_balance}, требуется: {user_context.bot_params.order_size}")
                await update.message.reply_text(
                    f"❌ Недостаточно средств для торговли.\n"
                    f"Доступно: {usdt_balance} USDT\n"
                    f"Требуется: {user_context.bot_params.order_size} USDT"
                )
                bot_state_manager.stop(user_id)
                return

            await update.message.reply_text("✅ Баланс достаточен для торговли")
        except Exception as e:
            logger.error(f"Ошибка при проверке баланса: {e}")
            await update.message.reply_text(f"❌ Ошибка при проверке баланса: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Проверяем наличие торговой пары
        logger.info(f"Проверка наличия торговой пары {symbol}")
        await update.message.reply_text(f"🔄 Проверка доступности {symbol}...")

        try:
            mexc_instance.load_markets()
            if symbol not in mexc_instance.markets:
                logger.error(f"Торговая пара {symbol} не найдена на бирже")
                await update.message.reply_text(f"❌ Торговая пара {symbol} не найдена на бирже MEXC")
                bot_state_manager.stop(user_id)
                return

            logger.info(f"Торговая пара {symbol} доступна для торговли")
            await update.message.reply_text(f"✅ Пара {symbol} доступна для торговли")
        except Exception as e:
            logger.error(f"Ошибка при проверке торговой пары: {e}")
            await update.message.reply_text(f"❌ Ошибка при проверке доступности {symbol}: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Получаем текущую цену
        logger.info(f"Получение текущей цены для {symbol}")
        await update.message.reply_text(f"🔄 Получение текущей цены {symbol}...")

        try:
            ticker = mexc_instance.fetch_ticker(symbol)
            current_price = ticker['last']
            logger.info(f"Текущая цена {symbol}: {current_price}")
            await update.message.reply_text(f"💲 Текущая цена {symbol}: {current_price}")
        except Exception as e:
            logger.error(f"Ошибка при получении текущей цены: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении цены {symbol}: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Подготовка к покупке
        logger.info(f"Подготовка к созданию ордера на покупку")
        await update.message.reply_text("🔄 Подготовка к покупке...")

        # Установка цены покупки
        user_context.bot_params.buy_price = current_price
        logger.info(f"Цена покупки установлена: {user_context.bot_params.buy_price}")

        # Определяем размер ордера
        cost = user_context.bot_params.order_size
        logger.info(f"Размер ордера: {cost} USDT")

        # Получаем информацию о минимальных требованиях
        try:
            market = mexc_instance.markets[symbol]

            # Проверяем наличие информации о минимальном размере ордера
            min_cost = None
            if 'limits' in market and 'cost' in market['limits'] and 'min' in market['limits']['cost']:
                min_cost = float(market['limits']['cost']['min'])
                logger.info(f"Минимальный размер ордера: {min_cost} USDT")

            min_amount = None
            if 'limits' in market and 'amount' in market['limits'] and 'min' in market['limits']['amount']:
                min_amount = float(market['limits']['amount']['min'])
                logger.info(f"Минимальное количество: {min_amount}")

            # Расчет количества монет
            amount = cost / current_price
            logger.info(f"Расчетное количество для покупки: {amount}")

            # Проверяем, соответствует ли количество минимальным требованиям
            if min_amount is not None and amount < min_amount:
                logger.warning(f"Расчетное количество ({amount}) меньше минимального ({min_amount}). Корректируем.")
                amount = min_amount
                cost = amount * current_price
                logger.info(f"Скорректированная стоимость: {cost} USDT")
                await update.message.reply_text(
                    f"⚠️ Рассчитанное количество меньше минимального.\n"
                    f"Увеличиваем заказ до минимального: {amount} {symbol.split('/')[0]} (≈{cost} USDT)"
                )

            precision = 8  # По умолчанию
            if 'precision' in market and 'amount' in market['precision']:
                prec_value = market['precision']['amount']
                logger.info(f"Исходное значение precision для amount: {prec_value} (тип: {type(prec_value).__name__})")

                # Конвертируем precision в целое число
                if isinstance(prec_value, float):
                    # Если precision - дробное число меньше 1 (например 0.01),
                    # преобразуем его в количество десятичных знаков
                    if prec_value < 1:
                        precision = abs(int(math.log10(prec_value)))
                    else:
                        precision = int(prec_value)
                elif prec_value is not None:
                    try:
                        precision = int(prec_value)
                    except (ValueError, TypeError):
                        logger.error(f"Невозможно преобразовать precision в целое число: {prec_value}")
                        precision = 8  # Используем значение по умолчанию

            logger.info(f"Итоговая точность для количества: {precision}")
            amount = round(amount, precision)

            await update.message.reply_text(
                f"📝 Параметры ордера:\n"
                f"- Символ: {symbol}\n"
                f"- Количество: {amount}\n"
                f"- Примерная цена: {current_price}\n"
                f"- Общая стоимость: ≈{cost} USDT"
            )
        except Exception as e:
            logger.error(f"Ошибка при получении информации о минимальных требованиях: {e}")
            await update.message.reply_text(f"❌ Ошибка при подготовке ордера: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Выполняем покупку
        logger.info(f"Создание рыночного ордера на покупку {amount} {symbol.split('/')[0]}")
        await update.message.reply_text("🔄 Создание ордера на покупку...")

        try:
            # Пробуем покупку методом 1: Указание количества
            try:
                logger.info(f"Попытка покупки методом 1 (указание количества)...")
                buy_order = mexc_instance.create_market_buy_order(symbol, amount)
                logger.info(f"Ордер на покупку успешно создан (метод 1): {buy_order}")

                await update.message.reply_text(
                    f"✅ Покупка выполнена успешно!\n"
                    f"- Символ: {symbol}\n"
                    f"- Количество: {amount}\n"
                    f"- Цена: ≈{current_price}\n"
                    f"- Стоимость: ≈{cost} USDT"
                )
            except Exception as e:
                logger.error(f"Ошибка при создании ордера методом 1: {e}")
                logger.info(f"Попытка покупки методом 2 (quoteOrderQty)...")

                # Пробуем покупку методом 2: Использование quoteOrderQty
                params = {'quoteOrderQty': cost}
                buy_order = mexc_instance.create_market_buy_order(symbol, None, None, params)
                logger.info(f"Ордер на покупку успешно создан (метод 2): {buy_order}")

                await update.message.reply_text(
                    f"✅ Покупка выполнена успешно (метод 2)!\n"
                    f"- Символ: {symbol}\n"
                    f"- Стоимость: {cost} USDT"
                )

            # Обновляем состояние после успешной покупки
            user_context.current_level += 1
            user_context.buy_executed[symbol] = True

            # Получаем фактическое количество купленных монет
            actual_amount = buy_order.get('amount', amount)
            logger.info(f"Фактическое количество купленных монет: {actual_amount}")

            # Рассчитываем цену продажи
            sell_price = current_price * (1 + user_context.bot_params.profit_percentage / 100)
            logger.info(f"Расчетная цена продажи: {sell_price}")

            # Округляем цену продажи с учетом точности
            # Округляем цену продажи с учетом точности
            price_precision = 8  # По умолчанию
            if 'precision' in market and 'price' in market['precision']:
                prec_value = market['precision']['price']
                logger.info(f"Исходное значение precision для price: {prec_value} (тип: {type(prec_value).__name__})")

                # Конвертируем precision в целое число
                if isinstance(prec_value, float):
                    # Если precision - дробное число меньше 1 (например 0.01),
                    # преобразуем его в количество десятичных знаков
                    if prec_value < 1:
                        price_precision = abs(int(math.log10(prec_value)))
                    else:
                        price_precision = int(prec_value)
                elif prec_value is not None:
                    try:
                        price_precision = int(prec_value)
                    except (ValueError, TypeError):
                        logger.error(f"Невозможно преобразовать price_precision в целое число: {prec_value}")
                        price_precision = 8  # Используем значение по умолчанию

            logger.info(f"Итоговая точность для цены: {price_precision}")
            sell_price = round(sell_price, price_precision)

            # Создаем ордер на продажу
            logger.info(
                f"Создание лимитного ордера на продажу {actual_amount} {symbol.split('/')[0]} по цене {sell_price}")
            await update.message.reply_text(f"🔄 Создание ордера на продажу по цене {sell_price}...")

            try:
                sell_order = mexc_instance.create_limit_sell_order(symbol, actual_amount, sell_price)
                logger.info(f"Ордер на продажу успешно создан: {sell_order}")

                await update.message.reply_text(
                    f"✅ Ордер на продажу создан успешно!\n"
                    f"- Символ: {symbol}\n"
                    f"- Количество: {actual_amount}\n"
                    f"- Цена продажи: {sell_price}\n"
                    f"- Ожидаемая прибыль: {user_context.bot_params.profit_percentage}%"
                )
            except Exception as e:
                logger.error(f"Ошибка при создании ордера на продажу: {e}")
                await update.message.reply_text(f"❌ Ошибка при создании ордера на продажу: {str(e)}")
                # Продолжаем, т.к. монеты уже куплены, и пользователь может продать их вручную

            # Логируем успешное завершение первой покупки
            logger.info(f"Первая покупка и продажа успешно выполнены для пользователя {user_id}")
            await update.message.reply_text(
                "✅ Автоторговля выполнила первый цикл покупки и продажи.\n"
                "Ожидаем исполнения ордера на продажу..."
            )

        except Exception as e:
            logger.error(f"Ошибка при создании ордера на покупку: {e}")
            logger.error(traceback.format_exc())  # Полный стек-трейс
            await update.message.reply_text(f"❌ Ошибка при создании ордера на покупку: {str(e)}")
            bot_state_manager.stop(user_id)
            return

        # Ожидаем завершения торговли
        logger.info(f"Ожидание завершения торговли для пользователя {user_id}")

        iteration = 0
        while bot_state_manager.is_trading_active(user_id):
            iteration += 1
            logger.info(f"Итерация ожидания #{iteration} для пользователя {user_id}")

            # Добавляем проверку статуса ордера на продажу каждые 30 секунд
            if iteration % 3 == 0:  # Каждые ~30 секунд (10 секунд между итерациями)
                try:
                    # Проверка открытых ордеров
                    open_orders = mexc_instance.fetch_open_orders(symbol)
                    num_open_orders = len(open_orders)
                    logger.info(f"Количество открытых ордеров: {num_open_orders}")

                    if num_open_orders > 0:
                        logger.info(f"Ордер на продажу все еще открыт. Ожидаем исполнения.")
                    else:
                        logger.info(f"Все ордеры исполнены! Цикл автоторговли завершен.")
                        await update.message.reply_text(
                            "🎉 Все ордеры исполнены! Цикл торговли завершен успешно."
                        )
                        # Можно добавить логику для следующего цикла автоторговли здесь
                except Exception as e:
                    logger.error(f"Ошибка при проверке статуса ордеров: {e}")

            # Ждем 10 секунд между проверками
            await asyncio.sleep(10)

        logger.info(f"Автоторговля остановлена для пользователя {user_id}")
        await update.message.reply_text("⏹️ Автоторговля остановлена.")

    except Exception as e:
        logger.error(f"Неожиданная ошибка в автоторговле: {e}")
        logger.error(traceback.format_exc())  # Полный стек-трейс
        await update.message.reply_text(f"❌ Неожиданная ошибка: {str(e)}")
    finally:
        # Обязательно останавливаем автоторговлю при выходе из функции
        bot_state_manager.stop(user_id)
        logger.info(f"========== КОНЕЦ АВТОТОРГОВЛИ ==========")