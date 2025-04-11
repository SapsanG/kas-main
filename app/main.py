# app/main.py

import os
import sys
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
# Добавляем корневую директорию проекта в sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)
# Абсолютные импорты
from config.config import TOKEN, DATABASE_URL, ADMIN_ID
from app.database import init_db, db_session  # Инициализация базы данных
from config.logging_config import logger

# Глобальная переменная application
application = None

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Скрыть INFO-сообщения httpx

# Главная функция
def main() -> None:
    global application  # Используем глобальную переменную
    try:
        # Инициализация базы данных
        init_db()
        logger.info("База данных успешно инициализирована.")

        logger.info("Бот успешно запущен!")
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        from app.handlers import start
        from app.buy_handlers import buy, balance
        from app.profit_handlers import profit_today, profit_history, profit_month, profit_total
        from app.settings_handlers import set_params, set_api_keys, check_api_keys, stats, reset_trading
        from app.autotrade_handlers import autobuy, stop

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("buy", buy))
        application.add_handler(CommandHandler("balance", balance))
        application.add_handler(CommandHandler("set_params", set_params))
        application.add_handler(CommandHandler("autobuy", autobuy))
        application.add_handler(CommandHandler("stop", stop))
        application.add_handler(CommandHandler("set_api_keys", set_api_keys))
        application.add_handler(CommandHandler("check_api_keys", check_api_keys))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("profit_today", profit_today))
        application.add_handler(CommandHandler("profit_history", profit_history))
        application.add_handler(CommandHandler("profit_month", profit_month))
        application.add_handler(CommandHandler("profit_total", profit_total))
        application.add_handler(CommandHandler("reset_trading", reset_trading))

        application.run_polling()
    
    except Exception as e:
        error_message = f"Критическая ошибка при запуске бота: {e}"
        logger.error(error_message)
        asyncio.run(send_error_notification(error_message))

# Функция для отправки уведомлений администратору
async def send_error_notification(error_message: str):
    global application  # Используем глобальную переменную
    if application:
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text=f"Ошибка в боте:\n{error_message}")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору: {e}")

# Точка входа в программу
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        error_message = f"Неизвестная ошибка: {e}"
        logger.error(error_message)
        asyncio.run(send_error_notification(error_message))
    finally:
        # Закрываем сессию базы данных
        if db_session:
            db_session.close()
            logger.info("Сессия базы данных закрыта.")
        logger.info("Завершение работы бота...")