# app/profit_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context  # Импортируем get_user_context
from config.logging_config import logger

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Команда /profit_today
async def profit_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /profit_today вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    try:
        # Вычисляем профит за сегодня
        profit = user_context.calculate_profit_today()
        await update.message.reply_text(f'Ваш профит за сегодня: ${profit:.2f}')
    
    except Exception as e:
        logger.error(f"Ошибка при расчете профита за сегодня для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Команда /profit_history
async def profit_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /profit_history вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if len(context.args) != 1:
        await update.message.reply_text('Использование: /profit_history <дни>')
        return
    
    try:
        days = int(context.args[0])
        if days <= 0:
            raise ValueError("Количество дней должно быть положительным числом.")
        
        # Вычисляем профит за указанный период
        profit = user_context.calculate_profit_period(days)
        await update.message.reply_text(f'Ваш профит за последние {days} дней: ${profit:.2f}')
    
    except ValueError as e:
        logger.error(f"Ошибка валидации периода для пользователя {user_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}')
    except Exception as e:
        logger.error(f"Ошибка при расчете профита за период для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Команда /profit_month
async def profit_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /profit_month вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    try:
        # Вычисляем профит за последний месяц
        profit = user_context.calculate_profit_month()
        await update.message.reply_text(f'Ваш профит за последний месяц: ${profit:.2f}')
    
    except Exception as e:
        logger.error(f"Ошибка при расчете профита за месяц для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Команда /profit_total
async def profit_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /profit_total вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    try:
        # Вычисляем общий профит
        profit = user_context.calculate_profit_total()
        await update.message.reply_text(f'Ваш общий профит: ${profit:.2f}')
    
    except Exception as e:
        logger.error(f"Ошибка при расчете общего профита для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")