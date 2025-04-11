# settings_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context, bot_state_manager  # Импортируем get_user_context
from config.logging_config import logger

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Определение класса ValidationError
class ValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

# Валидация положительного числа
def validate_positive_number(value, field_name):
    if value <= 0:
        raise ValidationError(f"{field_name} должно быть положительным числом.")

# Команда /set_params
async def set_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /set_params вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    # Формируем сообщение с текущими параметрами
    current_params_message = (
        f"Текущие параметры:\n"
        f"Процент прибыли: {user_context.bot_params.profit_percentage}%\n"
        f"Процент падения: {user_context.bot_params.fall_percentage}%\n"
        f"Задержка: {user_context.bot_params.delay_seconds} секунд\n"
        f"Размер ордера: ${user_context.bot_params.order_size}\n\n"
        f"Использование: /set_params <процент_прибыли> <процент_падения> <задержка> <размер_ордера>\n"
        f"Пример: /set_params 0.5 1.2 60 50"
    )
    
    # Проверяем количество аргументов
    if len(context.args) != 4:
        await update.message.reply_text(current_params_message)
        return
    
    try:
        profit_percentage = float(context.args[0])
        fall_percentage = float(context.args[1])
        delay_seconds = int(context.args[2])
        order_size = float(context.args[3])
        
        # Валидация параметров
        validate_positive_number(profit_percentage, "Процент прибыли")
        validate_positive_number(fall_percentage, "Процент падения")
        validate_positive_number(delay_seconds, "Задержка")
        validate_positive_number(order_size, "Размер ордера")
        
        old_params = {
            "profit_percentage": user_context.bot_params.profit_percentage,
            "fall_percentage": user_context.bot_params.fall_percentage,
            "delay_seconds": user_context.bot_params.delay_seconds,
            "order_size": user_context.bot_params.order_size,
        }
        
        # Устанавливаем новые параметры
        user_context.bot_params.set_params(profit_percentage, fall_percentage, delay_seconds, order_size)
        user_context.save_user_params()  # Сохраняем изменения в базе данных
        
        logger.info(f"Параметры успешно сохранены для пользователя {user_id}.")
        
        if (
            old_params["profit_percentage"] == user_context.bot_params.profit_percentage and
            old_params["fall_percentage"] == user_context.bot_params.fall_percentage and
            old_params["delay_seconds"] == user_context.bot_params.delay_seconds and
            old_params["order_size"] == user_context.bot_params.order_size
        ):
            await update.message.reply_text(
                f'Параметры не изменились.\n'
                f'{current_params_message}'
            )
        else:
            await update.message.reply_text(
                f'Параметры успешно обновлены:\n'
                f'Процент прибыли: {user_context.bot_params.profit_percentage}%\n'
                f'Процент падения: {user_context.bot_params.fall_percentage}%\n'
                f'Задержка: {user_context.bot_params.delay_seconds} секунд\n'
                f'Размер ордера: ${user_context.bot_params.order_size}\n\n'
                f'Для установки новых параметров используйте:\n'
                f'/set_params <процент_прибыли> <процент_падения> <задержка> <размер_ордера>\n'
                f'Пример: /set_params 0.5 1.2 60 50'
            )
    
    except ValidationError as e:
        logger.error(f"Ошибка валидации параметров для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}\n{current_params_message}')
    except ValueError as e:
        logger.error(f"Ошибка преобразования параметров для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: все параметры должны быть числами.\n{current_params_message}')

# Команда /set_api_keys
async def set_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /set_api_keys вызвана пользователем {user_id}")
    
    if len(context.args) != 2:
        await update.message.reply_text('Использование: /set_api_keys <api_key> <api_secret>')
        return
    
    api_key = context.args[0]
    api_secret = context.args[1]
    
    try:
        # Получаем контекст пользователя
        user_context = get_user_context(user_id)
        
        # Устанавливаем API-ключи
        user_context.set_api_credentials(api_key, api_secret)
        user_context.save_user_params()  # Сохраняем изменения в базе данных
        
        logger.info(f"API-ключи успешно сохранены для пользователя {user_id}.")
        
        await update.message.reply_text('API-ключи успешно установлены.')
    
    except ValidationError as e:
        logger.error(f"Ошибка валидации API-ключей для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}')
    except Exception as e:
        logger.error(f"Ошибка при установке API-ключей для пользователя {user_id}: {e}")
        await update.message.reply_text('Ошибка при установке API-ключей.')

# Команда /check_api_keys
async def check_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /check_api_keys вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if user_context.api_key and user_context.api_secret:
        logger.info(f"API-ключи успешно загружены для пользователя {user_id}.")
        await update.message.reply_text(f'Ваши API-ключи:\nAPI Key: {user_context.api_key}\nAPI Secret: {user_context.api_secret}')
    else:
        logger.warning(f"API-ключи не найдены для пользователя {user_id}.")
        await update.message.reply_text('API-ключи не установлены.')

# Команда /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /stats вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    reply = (
        f"Статистика торговли для пользователя {user_id}:\n"
        f"Текущий уровень: {user_context.current_level}\n"
        f"Выполненные покупки: {list(user_context.buy_executed.keys())}\n"
        f"Текущая цена покупки: ${user_context.bot_params.buy_price or 'Не определена'}\n"
    )
    await update.message.reply_text(reply)


# Добавьте эту функцию в файл settings_handlers.py

# Команда /reset_trading
async def reset_trading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /reset_trading вызвана пользователем {user_id}")

    previous_state = bot_state_manager.is_trading_active(user_id)

    if previous_state:
        bot_state_manager.stop(user_id)
        logger.info(f"Состояние автоторговли сброшено для пользователя {user_id}")
        await update.message.reply_text("✅ Состояние автоторговли сброшено. Теперь вы можете запустить новую сессию.")
    else:
        logger.info(f"Автоторговля не была активна для пользователя {user_id}")
        await update.message.reply_text("ℹ️ Автоторговля не запущена, сброс не требуется.")