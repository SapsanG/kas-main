# debugging_trading_logic.py
# Запустите этот скрипт для отладки покупки

import logging
import asyncio
import sys
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Установка уровня DEBUG для получения всех сообщений
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler("debug.log")  # Запись в файл
    ]
)
logger = logging.getLogger("debug_trading")

# Добавляем корневую директорию проекта в sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)


async def debug_buy():
    try:
        from app.database import User, db_session, encryption_manager
        from app.contexts import UserContext
        import ccxt

        # Установка Telegram ID пользователя для отладки
        user_id = 810668767  # Замените на свой ID

        logger.info(f"Начало отладки для пользователя {user_id}")

        # Получаем данные пользователя из БД
        with db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.error(f"Пользователь {user_id} не найден в базе данных")
                return

            logger.info(f"Найден пользователь: {user.id}")
            logger.info(f"Размер ордера: {user.order_size}")

            if not user.api_key_encrypted or not user.api_secret_encrypted:
                logger.error("API ключи отсутствуют или не зашифрованы")
                return

            # Расшифровываем ключи
            try:
                api_key = encryption_manager.decrypt(user.api_key_encrypted)
                api_secret = encryption_manager.decrypt(user.api_secret_encrypted)
                logger.info("API ключи успешно расшифрованы")
            except Exception as e:
                logger.error(f"Ошибка при расшифровке API ключей: {e}")
                return

        # Создаем экземпляр MEXC
        logger.info("Создаем экземпляр MEXC...")
        mexc = ccxt.mexc({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'createMarketBuyOrderRequiresPrice': False
            }
        })

        # Проверяем соединение с биржей
        logger.info("Проверка соединения с биржей...")
        try:
            markets = mexc.load_markets()
            logger.info(f"Соединение успешно. Доступно {len(markets)} рынков")
        except Exception as e:
            logger.error(f"Ошибка при соединении с биржей: {e}")
            return

        # Получаем баланс
        logger.info("Получение баланса...")
        try:
            balance = mexc.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            logger.info(f"Баланс USDT: {usdt_balance}")

            if usdt_balance < user.order_size:
                logger.error(f"Недостаточно средств. Требуется {user.order_size}, доступно {usdt_balance}")
                return
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return

        # Символ для покупки
        symbol = "KAS/USDT"
        logger.info(f"Проверка символа {symbol}...")

        # Проверяем, есть ли такой символ на бирже
        if symbol not in mexc.markets:
            logger.error(f"Символ {symbol} не найден на бирже")
            return

        logger.info(f"Символ {symbol} доступен для торговли")

        # Получаем текущую цену
        try:
            ticker = mexc.fetch_ticker(symbol)
            current_price = ticker['last']
            logger.info(f"Текущая цена {symbol}: {current_price}")
        except Exception as e:
            logger.error(f"Ошибка при получении цены: {e}")
            return

        # Проверяем минимальные требования
        logger.info("Проверка минимальных требований для ордера...")
        market = mexc.markets[symbol]

        min_cost = market['limits']['cost']['min'] if 'limits' in market and 'cost' in market['limits'] and 'min' in \
                                                      market['limits']['cost'] else None
        min_amount = market['limits']['amount']['min'] if 'limits' in market and 'amount' in market[
            'limits'] and 'min' in market['limits']['amount'] else None

        logger.info(f"Минимальная стоимость: {min_cost}, минимальное количество: {min_amount}")

        cost = user.order_size
        if min_cost and cost < float(min_cost):
            logger.error(f"Размер ордера ({cost}) меньше минимального ({min_cost})")
            return

        # Пробуем разные методы покупки

        # Метод 1: Стандартный метод с указанием суммы
        logger.info("Попытка покупки - Метод 1 (стандартный)...")
        try:
            # Рассчитываем количество монет, которое мы можем купить
            amount = cost / current_price
            logger.info(f"Расчетное количество для покупки: {amount}")

            # Проверяем минимальное количество
            if min_amount and amount < float(min_amount):
                logger.warning(f"Расчетное количество ({amount}) меньше минимального ({min_amount})")
                # Увеличиваем до минимального
                amount = float(min_amount)
                logger.info(f"Увеличиваем количество до минимального: {amount}")

            # Создаем рыночный ордер на покупку с указанием количества
            order = mexc.create_market_buy_order(symbol, amount)
            logger.info(f"Ордер успешно создан: {order}")
            return
        except Exception as e:
            logger.error(f"Ошибка при создании ордера (Метод 1): {e}")

        # Метод 2: Использование параметра quoteOrderQty
        logger.info("Попытка покупки - Метод 2 (quoteOrderQty)...")
        try:
            params = {
                'quoteOrderQty': cost
            }
            order = mexc.create_market_buy_order(symbol, None, None, params)
            logger.info(f"Ордер успешно создан: {order}")
            return
        except Exception as e:
            logger.error(f"Ошибка при создании ордера (Метод 2): {e}")

        # Метод 3: Использование createOrder с типом MARKET
        logger.info("Попытка покупки - Метод 3 (createOrder)...")
        try:
            params = {
                'quoteOrderQty': cost
            }
            order = mexc.create_order(symbol, 'market', 'buy', None, None, params)
            logger.info(f"Ордер успешно создан: {order}")
            return
        except Exception as e:
            logger.error(f"Ошибка при создании ордера (Метод 3): {e}")

        logger.error("Все методы покупки завершились с ошибкой")

    except Exception as e:
        logger.error(f"Неизвестная ошибка при отладке: {e}")


# Запуск функции отладки
if __name__ == "__main__":
    asyncio.run(debug_buy())