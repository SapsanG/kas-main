# trading_logic.py

import asyncio
import logging
import math
from app.shared import bot_state_manager, get_user_context
from telegram import Update
import ccxt
import time

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

    try:
        user_context = get_user_context(user_id)
        logger.info(f"Контекст пользователя {user_id} загружен")
        await update.message.reply_text("✅ Контекст загружен")
    except Exception as e:
        logger.error(f"Ошибка контекста: {e}")
        await update.message.reply_text(f"❌ Ошибка контекста: {str(e)}")
        return

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
        mexc = user_context.get_mexc_instance()
        await update.message.reply_text("✅ Подключено к MEXC")

        balance = mexc.fetch_balance()
        usdt_balance = balance['USDT']['free']
        logger.info(f"Баланс USDT: {usdt_balance}")
        await update.message.reply_text(f"💰 Баланс: {usdt_balance} USDT")
        
        if usdt_balance < user_context.bot_params.order_size:
            await update.message.reply_text("❌ Недостаточно средств")
            bot_state_manager.stop(user_id)
            return

        mexc.load_markets()
        if symbol not in mexc.markets:
            await update.message.reply_text(f"❌ Пара {symbol} не найдена")
            bot_state_manager.stop(user_id)
            return

        market = mexc.markets[symbol]
        price_precision = market['precision']['price']
        amount_precision = market['precision']['amount']

        last_buy_time = 0
        last_buy_price = 0
        buy_levels = []
        sell_orders = []

        while bot_state_manager.is_trading_active(user_id):
            try:
                ticker = mexc.fetch_ticker(symbol)
                current_bid = float(ticker['bid'])  # Лучшая цена покупателей
                current_ask = float(ticker['ask'])  # Лучшая цена продавцов
                current_last = float(ticker['last'])  # Последняя цена сделки
                
                logger.info(f"Цены: Last={current_last}, BID={current_bid}, ASK={current_ask}")

                # Первая покупка
                if not buy_levels:
                    amount = user_context.bot_params.order_size / current_ask
                    amount = max(amount, market['limits']['amount']['min'])
                    amount = mexc.amount_to_precision(symbol, amount)
                    
                    buy_order = mexc.create_market_buy_order(symbol, amount)
                    buy_price = float(buy_order['price'])
                    actual_amount = float(buy_order['amount'])
                    
                    # Цена продажи рассчитывается от цены покупки через BID
                    sell_price = current_bid * (1 + user_context.bot_params.profit_percentage / 100)
                    sell_price = mexc.price_to_precision(symbol, sell_price)
                    
                    sell_order = mexc.create_limit_sell_order(symbol, actual_amount, sell_price)
                    profit = (float(sell_price) - buy_price) * actual_amount
                    
                    buy_levels.append({'price': buy_price, 'amount': actual_amount})
                    sell_orders.append({'id': sell_order['id'], 'profit': profit})
                    
                    last_buy_time = time.time()
                    last_buy_price = buy_price
                    
                    await update.message.reply_text(
                        f"✅ Покупка Buy1:\n"
                        f"- Цена: {buy_price}\n"
                        f"- Количество: {actual_amount}\n"
                        f"- Стоимость: {actual_amount * buy_price:.2f} USDT"
                    )
                    await update.message.reply_text(
                        f"🔄 Ордер на продажу:\n"
                        f"- Цена: {sell_price}\n"
                        f"- Ожидаемая прибыль: {profit:.2f} USDT"
                    )
                    continue

                # Проверка условий для следующей покупки
                time_condition = (time.time() - last_buy_time) >= user_context.bot_params.delay_seconds
                price_condition = current_last <= last_buy_price * (1 - user_context.bot_params.fall_percentage / 100)
                
                if time_condition and price_condition:
                    amount = user_context.bot_params.order_size / current_ask
                    amount = max(amount, market['limits']['amount']['min'])
                    amount = mexc.amount_to_precision(symbol, amount)
                    
                    buy_order = mexc.create_market_buy_order(symbol, amount)
                    buy_price = float(buy_order['price'])
                    actual_amount = float(buy_order['amount'])
                    
                    sell_price = current_bid * (1 + user_context.bot_params.profit_percentage / 100)
                    sell_price = mexc.price_to_precision(symbol, sell_price)
                    
                    sell_order = mexc.create_limit_sell_order(symbol, actual_amount, sell_price)
                    profit = (float(sell_price) - buy_price) * actual_amount
                    
                    buy_levels.append({'price': buy_price, 'amount': actual_amount})
                    sell_orders.append({'id': sell_order['id'], 'profit': profit})
                    
                    last_buy_time = time.time()
                    last_buy_price = buy_price
                    
                    await update.message.reply_text(
                        f"✅ Покупка Buy{len(buy_levels)}:\n"
                        f"- Цена: {buy_price}\n"
                        f"- Количество: {actual_amount}\n"
                        f"- Стоимость: {actual_amount * buy_price:.2f} USDT"
                    )
                    await update.message.reply_text(
                        f"🔄 Ордер на продажу:\n"
                        f"- Цена: {sell_price}\n"
                        f"- Ожидаемая прибыль: {profit:.2f} USDT"
                    )

                # Проверка статуса ордеров
                open_orders = mexc.fetch_open_orders(symbol)
                active_order_ids = {o['id'] for o in open_orders}
                
                for order in sell_orders.copy():
                    if order['id'] not in active_order_ids:
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