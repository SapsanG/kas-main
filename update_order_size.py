# update_order_size.py

from app.database import User, db_session
from config.logging_config import logger

logger.info("Начинаем обновление размера ордера для всех пользователей.")

with db_session() as session:
    # Получаем всех пользователей
    users = session.query(User).all()

    if not users:
        logger.info("Пользователи не найдены.")
    else:
        for user in users:
            old_size = user.order_size
            user.order_size = 0.1  # Устанавливаем новый размер
            logger.info(f"Обновлен размер ордера для пользователя {user.id}: было {old_size}, стало 0.1")

        # Сохраняем изменения
        session.commit()

logger.info("Обновление размера ордера завершено.")