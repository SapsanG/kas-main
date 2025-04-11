# check_users.py

from app.database import User, db_session
from config.logging_config import logger

logger.info("Проверяем таблицу users.")

with db_session() as session:
    users = session.query(User).all()
    if not users:
        logger.info("Таблица users пуста.")
    else:
        for user in users:
            logger.info(f"User ID: {user.id}")
            logger.info(f"API Key Encrypted: {user.api_key_encrypted}")
            logger.info(f"API Secret Encrypted: {user.api_secret_encrypted}")
            logger.info(f"Profit Percentage: {user.profit_percentage}")
            logger.info(f"Fall Percentage: {user.fall_percentage}")
            logger.info(f"Delay Seconds: {user.delay_seconds}")
            logger.info(f"Order Size: {user.order_size}")