# shared.py

from app.database import User, db_session  # Импортируем User и db_session
from app.contexts import UserContext  # Импортируем UserContext

# Глобальный кэш для хранения экземпляров UserContext
user_context_cache = {}

# Класс для управления состоянием бота
class BotStateManager:
    def __init__(self):
        self.active_users = {}  # Словарь для отслеживания состояния торговли для каждого пользователя
    
    def start(self, user_id: int):
        """Запускает торговлю для указанного пользователя."""
        self.active_users[user_id] = True
    
    def stop(self, user_id: int):
        """Останавливает торговлю для указанного пользователя."""
        if user_id in self.active_users:
            self.active_users[user_id] = False
    
    def is_trading_active(self, user_id: int) -> bool:
        """Проверяет, активна ли торговля для указанного пользователя."""
        return self.active_users.get(user_id, False)

# Глобальный экземпляр BotStateManager
bot_state_manager = BotStateManager()

# Функция для получения или создания контекста пользователя
def get_user_context(user_id: int) -> 'UserContext':
    """
    Получает или создает контекст пользователя с использованием кэша.
    
    :param user_id: Уникальный идентификатор пользователя.
    :return: Экземпляр UserContext.
    """
    global user_context_cache
    
    # Проверяем, есть ли контекст пользователя в кэше
    if user_id not in user_context_cache:
        # Если нет, создаем новый экземпляр UserContext
        with db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                user = User(id=user_id)
                session.add(user)
                session.commit()
        user_context_cache[user_id] = UserContext(user_id)
    
    return user_context_cache[user_id]