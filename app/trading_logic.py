import asyncio
import logging
import json
from pathlib import Path
import time
import traceback
from app.shared import bot_state_manager, get_user_context
from telegram import Update
import ccxt

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def notify_sell_order_filled(update, order_id, profit):
    await update.message.reply_text(
        f"🎉 Ордер {order_id} исполнен! Прибыль: +{profit:.2f} USDT"
    )

def save_state(user_id, buy_levels, sell_orders):
    state = {
        'buy_levels': buy_levels,
        'sell_orders': [o['id'] for o in sell_orders],
    }
    with open(f"state_{user_id}.json", "w") as f:
        json.dump(state, f)

def load_state(user_id):
    try:
        with open(f"state_{user_id}.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {'buy_levels': [], 'sell_orders': []}

async def safe_api_call(api_function, *args, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return api_function(*args)
        except ccxt.NetworkError as e:
            logger.error(f"Сетевая ошибка (попытка {attempt + 1}/{retries}): {e}")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            raise
    raise Exception("Превышено количество попыток")

async def reset_state(update: Update) -> None:
    user_id = update.effective_user.id
    state_file = Path(f"state_{user_id}.json")
    if state_file.exists():
        state_file.unlink()
        logger.info(f"Состояние пользователя {user_id} сброшено.")
        await update.message.reply_text("✅ Состояние сброшено. Все уровни покупок удалены.")
    else:
        await update.message.reply_text("⚠️ Нет сохраненного состояния для сброса.")

async def start_trading(symbol: str, update: Update) -> None:
    user_id = update.effective_user.id
    logger.info(f"========== НАЧАЛО АВТОТОРГОВЛИ ==========")
    
    # Сброс предыдущей сессии
    if bot_state_manager.is_trading_active(user_id):
        logger.warning(f"Сброс предыдущей сессии для пользователя {user_id}")
        bot_state_manager.stop(user_id)
        await update.message.reply_text('Предыдущая сессия сброшена.')
    
    # Очистка файла состояния
    state_file = Path(f"state_{user_id}.json")
    if state_file.exists():
        state_file.unlink()
        logger.info("Файл состояния удален.")
    
    # Загрузка состояния
    state = load_state(user_id)
    buy_levels = state.get('buy_levels', [])
    sell_orders = [{'id': oid} for oid in state.get('sell_orders', [])]
    
    try:
        user_context = get_user_context(user_id)
        mexc = user_context.get_mexc_instance()
        
        # Установка обязательных параметров для спот-торговли
        mexc.options['defaultType'] = 'spot'  # <- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
        symbol = symbol.replace(':USDT', '')  # Убедимся, что символ в спот-формате
        
        # Проверка баланса
        balance = await safe_api_call(mexc.fetch_balance)
        usdt_balance = balance['USDT']['free']
        if usdt_balance < user_context.bot_params.order_size:
            raise Exception("Недостаточно средств")
        
        market = await safe_api_call(mexc.market, symbol)
        price_precision = market['precision']['price']
        amount_precision = market['precision']['amount']
        
        last_buy_time = time.time() if buy_levels else 0
        last_buy_price = buy_levels[-1]['price'] if buy_levels else 0
        
        bot_state_manager.start(user_id)
        logger.info(f"Баланс USDT: {usdt_balance:.2f}")
        
        if not buy_levels:
            await update.message.reply_text("🔄 Торговая сессия начата. Начальных уровней покупки нет.")
        else:
            await update.message.reply_text(f"🔄 Торговая сессия начата. Загружено {len(buy_levels)} уровней покупки.")
        
        while bot_state_manager.is_trading_active(user_id):
            try:
                ticker = await safe_api_call(mexc.fetch_ticker, symbol)
                current_bid = float(ticker['bid'])
                current_ask = float(ticker['ask'])
                current_last = float(ticker['last'])
                
                # Проверка исполненных ордеров
                open_orders = await safe_api_call(mexc.fetch_open_orders, symbol)
                active_order_ids = {o['id'] for o in open_orders}
                
                # Проверка ордеров на продажу
                for order in sell_orders.copy():
                    if order['id'] not in active_order_ids:
                        sell_orders.remove(order)
                        await notify_sell_order_filled(update, order['id'], order.get('profit', 0))
                        save_state(user_id, buy_levels, sell_orders)
                        logger.info(f"Ордер {order['id']} исполнен. Осталось ордеров: {len(sell_orders)}")
                        
                        # Сброс уровней после исполнения ордера
                        buy_levels = []
                        last_buy_time = 0
                        last_buy_price = 0
                        save_state(user_id, buy_levels, sell_orders)
                        await update.message.reply_text("🔄 Сброс уровней покупки после исполнения ордера на продажу.")
                
                # Логика покупок
                if not buy_levels:
                    # Первая покупка
                    logger.info("Начальная покупка...")
                    amount = user_context.bot_params.order_size / current_ask
                    amount = max(amount, market['limits']['amount']['min'])
                    amount = mexc.amount_to_precision(symbol, amount)
                    amount = float(amount)
                    
                    buy_order = await safe_api_call(
                        mexc.create_market_buy_order,
                        symbol,
                        amount
                    )
                    
                    actual_amount = float(buy_order['amount'])
                    buy_price = current_ask
                    sell_price = current_bid * (1 + user_context.bot_params.profit_percentage / 100)
                    sell_price = mexc.price_to_precision(symbol, sell_price)
                    sell_price = float(sell_price)
                    
                    sell_order = await safe_api_call(
                        mexc.create_limit_sell_order,
                        symbol,
                        actual_amount,
                        sell_price
                    )
                    
                    profit = (sell_price - buy_price) * actual_amount
                    buy_levels.append({'price': buy_price, 'amount': actual_amount})
                    sell_orders.append({'id': sell_order['id'], 'profit': profit})
                    last_buy_time = time.time()
                    last_buy_price = buy_price
                    save_state(user_id, buy_levels, sell_orders)
                    
                    await update.message.reply_text(
                        f"✅ Первая покупка Buy1:\n"
                        f"- Цена: {buy_price:.6f}\n"
                        f"- Количество: {actual_amount:.6f}\n"
                        f"- Стоимость: {actual_amount * buy_price:.2f} USDT"
                    )
                    await update.message.reply_text(
                        f"🔄 Ордер на продажу:\n"
                        f"- Цена: {sell_price:.6f}\n"
                        f"- Ожидаемая прибыль: {profit:.2f} USDT"
                    )
                    continue  # Пропуск основного цикла после первой покупки
                
                # Проверка условий для последующих покупок
                last_buy = buy_levels[-1]
                time_condition = (time.time() - last_buy_time) >= user_context.bot_params.delay_seconds
                price_condition = current_last <= last_buy['price'] * (1 - user_context.bot_params.fall_percentage / 100)
                
                if time_condition and price_condition:
                    has_open_buy = any(o['side'] == 'buy' for o in open_orders)
                    if has_open_buy:
                        logger.info("Есть открытые ордера на покупку. Ожидание...")
                        await asyncio.sleep(10)
                        continue
                    
                    amount = user_context.bot_params.order_size / current_ask
                    amount = max(amount, market['limits']['amount']['min'])
                    amount = mexc.amount_to_precision(symbol, amount)
                    amount = float(amount)
                    
                    buy_order = await safe_api_call(
                        mexc.create_market_buy_order,
                        symbol,
                        amount
                    )
                    
                    actual_amount = float(buy_order['amount'])
                    buy_price = current_ask
                    sell_price = current_bid * (1 + user_context.bot_params.profit_percentage / 100)
                    sell_price = mexc.price_to_precision(symbol, sell_price)
                    sell_price = float(sell_price)
                    
                    sell_order = await safe_api_call(
                        mexc.create_limit_sell_order,
                        symbol,
                        actual_amount,
                        sell_price
                    )
                    
                    profit = (sell_price - buy_price) * actual_amount
                    buy_levels.append({'price': buy_price, 'amount': actual_amount})
                    sell_orders.append({'id': sell_order['id'], 'profit': profit})
                    last_buy_time = time.time()
                    last_buy_price = buy_price
                    save_state(user_id, buy_levels, sell_orders)
                    
                    await update.message.reply_text(
                        f"✅ Покупка Buy{len(buy_levels)}:\n"
                        f"- Цена: {buy_price:.6f}\n"
                        f"- Количество: {actual_amount:.6f}\n"
                        f"- Стоимость: {actual_amount * buy_price:.2f} USDT"
                    )
                    await update.message.reply_text(
                        f"🔄 Ордер на продажу:\n"
                        f"- Цена: {sell_price:.6f}\n"
                        f"- Ожидаемая прибыль: {profit:.2f} USDT"
                    )
                
                await asyncio.sleep(10)
            except ccxt.NetworkError as e:
                logger.error(f"Сетевая ошибка: {e}")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Ошибка цикла: {traceback.format_exc()}")
                await update.message.reply_text(f"❌ Ошибка: {str(e)}")
                await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"Критическая ошибка: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Критическая ошибка: {str(e)}")
    finally:
        bot_state_manager.stop(user_id)
        save_state(user_id, buy_levels, sell_orders)
        logger.info(f"========== КОНЕЦ АВТОТОРГОВЛИ ==========")