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

async def start_trading(symbol: str, update: Update) -> None:
    user_id = update.effective_user.id
    logger.info(f"========== НАЧАЛО АВТОТОРГОВЛИ ==========")
    logger.info(f"Автоторговля запущена для пользователя {user_id}, символ {symbol}")
    
    # Сброс предыдущего состояния
    await update.message.reply_text(f"🔄 Запускаю автоторговлю для {symbol}...")
    if bot_state_manager.is_trading_active(user_id):
        logger.warning(f"Сброс предыдущей сессии для пользователя {user_id}")
        bot_state_manager.stop(user_id)
        await update.message.reply_text('Предыдущая сессия сброшена.')

    # Инициализация контекста
    try:
        user_context = get_user_context(user_id)
        logger.info(f"Контекст пользователя {user_id} загружен")
        await update.message.reply_text("✅ Контекст загружен")
    except Exception as e:
        logger.error(f"Ошибка контекста: {e}")
        await update.message.reply_text(f"❌ Ошибка контекста: {str(e)}")
        return

    # Активация торговли
    bot_state_manager.start(user_id)
    logger.info(f"Параметры торговли для {user_id}:")
    logger.info(f"- Прибыль: {user_context.bot_params.profit_percentage}%")
    logger.info(f"- Падение: {user_context.bot_params.fall_percentage}%")
    logger.info(f"- Задержка: {user_context.bot_params.delay_seconds}с")
    logger.info(f"- Размер ордера: {user_context.bot_params.order_size} USDT")
    
    await update.message.reply_text(
        f"📊 Параметры:\n"
        f"- Прибыль: {user_context.bot_params.profit_percentage}%\n"
        f"- Падение: {user_context.bot_params.fall_percentage}%\n"
        f"- Задержка: {user_context.bot_params.delay_seconds}с\n"
        f"- Размер: {user_context.bot_params.order_size} USDT"
    )

    try:
        # Инициализация MEXC
        mexc = user_context.get_mexc_instance()
        await update.message.reply_text("✅ Подключено к MEXC")

        # Проверка баланса
        balance = mexc.fetch_balance()
        usdt_balance = balance['USDT']['free']
        logger.info(f"Баланс USDT: {usdt_balance}")
        await update.message.reply_text(f"💰 Баланс: {usdt_balance} USDT")
        
        if usdt_balance < user_context.bot_params.order_size:
            await update.message.reply_text("❌ Недостаточно средств")
            bot_state_manager.stop(user_id)
            return

        # Проверка торговой пары
        mexc.load_markets()
        if symbol not in mexc.markets:
            await update.message.reply_text(f"❌ Пара {symbol} не найдена")
            bot_state_manager.stop(user_id)
            return

        # Основные переменные
        last_buy_time = 0
        last_buy_price = 0
        buy_levels = []
        sell_orders = []

        while bot_state_manager.is_trading_active(user_id):
            try:
                current_price = mexc.fetch_ticker(symbol)['last']
                
                # Первая покупка
                if not buy_levels:
                    await execute_buy(
                        mexc, symbol, current_price, user_context, 
                        update, buy_levels, sell_orders
                    )
                    last_buy_time = time.time()
                    last_buy_price = current_price
                    continue  # Пропуск ожидания после первой покупки

                # Проверка условий для следующей покупки
                time_condition = (time.time() - last_buy_time) >= user_context.bot_params.delay_seconds
                price_condition = current_price <= last_buy_price * (1 - user_context.bot_params.fall_percentage/100)
                
                if time_condition and price_condition:
                    await execute_buy(
                        mexc, symbol, current_price, user_context, 
                        update, buy_levels, sell_orders
                    )
                    last_buy_time = time.time()
                    last_buy_price = current_price

                # Проверка статуса ордеров
                open_orders = mexc.fetch_open_orders(symbol)
                active_orders = {o['id'] for o in open_orders}
                for order in sell_orders.copy():
                    if order['id'] not in active_orders:
                        sell_orders.remove(order)
                        await update.message.reply_text(
                            f"🎉 Ордер {order['id']} исполнен! Прибыль: {order['profit']:.2f} USDT"
                        )

                await asyncio.sleep(10)
            except ccxt.NetworkError as e:
                logger.error(f"Сетевая ошибка: {e}")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Ошибка цикла: {e}")
                await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await update.message.reply_text(f"❌ Критическая ошибка: {str(e)}")
    finally:
        bot_state_manager.stop(user_id)
        logger.info(f"========== КОНЕЦ АВТОТОРГОВЛИ ==========")

async def execute_buy(mexc, symbol, price, user_context, update, buy_levels, sell_orders):
    """Выполнение покупки и создание ордера на продажу"""
    try:
        price = float(price)
        cost = user_context.bot_params.order_size
        market = mexc.markets[symbol]
        
        # Расчет количества с учетом минимальных требований
        min_amount = market['limits']['amount']['min']
        amount = max(cost / price, min_amount)
        amount = mexc.amount_to_precision(symbol, amount)
        
        # Выполнение покупки
        buy_order = mexc.create_market_buy_order(symbol, amount)
        buy_price = float(buy_order['price'])
        actual_amount = float(buy_order['amount'])
        
        logger.info(f"Покупка Buy{len(buy_levels)+1}: {actual_amount} по {buy_price}")
        await update.message.reply_text(
            f"✅ Покупка Buy{len(buy_levels)+1}:\n"
            f"- Цена: {buy_price}\n"
            f"- Количество: {actual_amount}\n"
            f"- Стоимость: {actual_amount * buy_price:.2f} USDT"
        )
        
        # Создание ордера на продажу
        sell_price = buy_price * (1 + user_context.bot_params.profit_percentage/100)
        sell_price = mexc.price_to_precision(symbol, sell_price)
        
        sell_order = mexc.create_limit_sell_order(symbol, actual_amount, sell_price)
        profit = (float(sell_price) - buy_price) * actual_amount
        
        buy_levels.append({'price': buy_price, 'amount': actual_amount})
        sell_orders.append({'id': sell_order['id'], 'profit': profit})
        
        await update.message.reply_text(
            f"🔄 Ордер на продажу создан:\n"
            f"- Цена: {sell_price}\n"
            f"- Ожидаемая прибыль: {profit:.2f} USDT"
        )

    except Exception as e:
        logger.error(f"Ошибка покупки: {e}")
        await update.message.reply_text(f"❌ Ошибка покупки: {str(e)}")