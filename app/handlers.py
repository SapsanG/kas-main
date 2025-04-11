# app/handlers.py

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

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /start вызвана пользователем {user_id}")
    
    # Получаем или создаем контекст пользователя
    user_context = get_user_context(user_id)
    
    await update.message.reply_text('Привет! Это торговый бот для биржи MEXC.\n'
                                    'Команды:\n'
                                    '/start - начать\n'
                                    '/balance - показать баланс\n'
                                    '/buy <symbol> <amount> - купить валюту\n'
                                    '/set_params <процент_прибыли> <процент_падения> <задержка> <размер_ордера> - установить параметры\n'
                                    '/autobuy - запустить автоматическую торговлю KAS/USDT\n'
                                    '/stop - остановить автоматическую торговлю\n'
                                    '/set_api_keys <api_key> <api_secret> - установить API-ключи\n'
                                    '/check_api_keys - проверить установленные API-ключи\n'
                                    '/stats - показать статистику\n'
                                    '/profit_today - показать профит за сегодня\n'
                                    '/profit_history <дни> - показать профит за указанный период\n'
                                    '/profit_month - показать профит за последний месяц\n'
                                    '/profit_total - показать общий профит')