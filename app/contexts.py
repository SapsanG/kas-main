# contexts.py

import ccxt
from datetime import datetime, timedelta
from app.database import User, TradeHistory, db_session, encryption_manager  # Импортируем необходимые компоненты из database.py
from config.logging_config import logger  # Добавляем импорт logger


class BotParams:
    def __init__(self, profit_percentage=0.3, fall_percentage=1.0, delay_seconds=30, order_size=40):
        self.profit_percentage = profit_percentage
        self.fall_percentage = fall_percentage
        self.delay_seconds = delay_seconds
        self.order_size = order_size
        self.buy_price = None

    def set_params(self, profit_percentage, fall_percentage, delay_seconds, order_size):
        self.profit_percentage = profit_percentage
        self.fall_percentage = fall_percentage
        self.delay_seconds = delay_seconds
        self.order_size = order_size


class UserContext:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.bot_params = self.load_user_params()
        self.api_key = None
        self.api_secret = None
        self.buy_executed = {}
        self.current_level = 0

    # Загрузка параметров пользователя из базы данных
    def load_user_params(self):
        with db_session() as session:
            user = session.query(User).filter_by(id=self.user_id).first()
            if user:
                # Загрузка API-ключей
                if user.api_key_encrypted and user.api_secret_encrypted:
                    try:
                        self.api_key = encryption_manager.decrypt(user.api_key_encrypted)
                        self.api_secret = encryption_manager.decrypt(user.api_secret_encrypted)
                        logger.info(f"API-ключи успешно загружены для пользователя {self.user_id}.")
                    except Exception as e:
                        logger.error(f"Ошибка при дешифровании API-ключей для пользователя {self.user_id}: {e}")
                        self.api_key = None
                        self.api_secret = None
                else:
                    logger.warning(f"Зашифрованные API-ключи отсутствуют для пользователя {self.user_id}.")

                # Загрузка параметров бота
                self.bot_params = BotParams(
                    profit_percentage=user.profit_percentage,
                    fall_percentage=user.fall_percentage,
                    delay_seconds=user.delay_seconds,
                    order_size=user.order_size
                )
        
        logger.info(f"Параметры успешно загружены для пользователя {self.user_id}.")
        return self.bot_params

    # Сохранение параметров пользователя в базу данных
    def save_user_params(self):
        with db_session() as session:
            user = session.query(User).filter_by(id=self.user_id).first()
            if not user:
                user = User(id=self.user_id)
                session.add(user)
            if self.api_key and self.api_secret:
                user.api_key_encrypted = encryption_manager.encrypt(self.api_key)
                user.api_secret_encrypted = encryption_manager.encrypt(self.api_secret)
            user.profit_percentage = self.bot_params.profit_percentage
            user.fall_percentage = self.bot_params.fall_percentage
            user.delay_seconds = self.bot_params.delay_seconds
            user.order_size = self.bot_params.order_size
            session.commit()
        logger.info(f"Параметры успешно сохранены для пользователя {self.user_id}.")

    # Установка API-ключей
    def set_api_credentials(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    # Получение экземпляра биржи MEXC
    def get_mexc_instance(self):
        if not self.api_key or not self.api_secret:
            raise ValueError("API-ключи не установлены.")
        return ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'createMarketBuyOrderRequiresPrice': False  # Разрешаем использование cost вместо amount
            }
        })

    # Логирование сделки в базу данных
    def log_trade(self, trade_type: str, symbol: str, amount: float, price: float, profit: float):
        with db_session() as session:
            trade = TradeHistory(
                user_id=self.user_id,
                trade_type=trade_type,
                symbol=symbol,
                amount=amount,
                price=price,
                profit=profit,
                timestamp=datetime.utcnow()
            )
            session.add(trade)
            session.commit()

    # Расчет профита за день
    def calculate_profit_today(self):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with db_session() as session:
            trades = session.query(TradeHistory).filter(
                TradeHistory.user_id == self.user_id,
                TradeHistory.trade_type == "sell",
                TradeHistory.timestamp >= today_start
            ).all()
        return sum(trade.profit for trade in trades)

    # Расчет профита за период
    def calculate_profit_period(self, days: int):
        period_start = datetime.now() - timedelta(days=days)
        with db_session() as session:
            trades = session.query(TradeHistory).filter(
                TradeHistory.user_id == self.user_id,
                TradeHistory.trade_type == "sell",
                TradeHistory.timestamp >= period_start
            ).all()
        return sum(trade.profit for trade in trades)

    # Расчет профита за месяц
    def calculate_profit_month(self):
        return self.calculate_profit_period(30)

    # Расчет профита за всё время
    def calculate_profit_total(self):
        with db_session() as session:
            trades = session.query(TradeHistory).filter(
                TradeHistory.user_id == self.user_id,
                TradeHistory.trade_type == "sell"
            ).all()
        return sum(trade.profit for trade in trades)