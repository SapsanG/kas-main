# clear_users.py

from app.database import User, db_session
from config.logging_config import logger

logger.info("Начинаем очистку таблицы users.")

with db_session() as session:
    # Удаляем все записи из таблицы users
    session.query(User).delete()
    session.commit()

logger.info("Таблица users успешно очищена.")