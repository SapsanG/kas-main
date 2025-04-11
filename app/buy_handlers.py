# buy_handlers.py

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
from app.shared import get_user_context  # Импортируем get_user_context
from config.logging_config import logger
import ccxt

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Команда /balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /balance вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    try:
        # Получаем экземпляр MEXC для пользователя
        mexc_instance = user_context.get_mexc_instance()
        
        # Получаем баланс
        balances = mexc_instance.fetch_balance()
        logger.info(f"Полный ответ fetch_balance() для пользователя {user_id}: {balances}")
        
        reply = "Ваш баланс:\n"
        for currency, balance_info in balances.items():
            if isinstance(balance_info, dict) and 'total' in balance_info and balance_info['total'] is not None and balance_info['total'] > 0:
                reply += f"{currency}: {balance_info['total']:.4f}\n"
        
        if not reply.strip():  # Если баланс пустой
            reply = "Ваш баланс пуст."
        
        await update.message.reply_text(reply)
    
    except ccxt.AuthenticationError as e:
        logger.error(f"Ошибка аутентификации для пользователя {user_id}: {e}")
        await update.message.reply_text("Ошибка аутентификации. Проверьте свои API-ключи.")
    except ccxt.NetworkError as e:
        logger.error(f"Ошибка сети при получении баланса для пользователя {user_id}: {e}")
        await update.message.reply_text("Не удалось получить баланс из-за сетевой ошибки. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при получении баланса для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Команда /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /buy вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if len(context.args) != 2:
        await update.message.reply_text('Использование: /buy <symbol> <cost>')
        return
    
    symbol = context.args[0].upper()
    cost = float(context.args[1])  # Сумма в долларах
    
    try:
        # Получаем экземпляр MEXC для пользователя
        mexc_instance = user_context.get_mexc_instance()
        
        # Выполняем покупку, используя cost (сумму в долларах)
        order = mexc_instance.create_market_buy_order(symbol, cost)
        
        logger.info(f"Выполнена покупка для пользователя {user_id}: {order}")
        await update.message.reply_text(
            f'Заказ выполнен успешно:\n'
            f'Символ: {symbol}\n'
            f'Общая стоимость: ${cost:.2f}'
        )
    
    except ccxt.InsufficientFunds as e:
        logger.error(f"Недостаточно средств для покупки для пользователя {user_id}: {e}")
        await update.message.reply_text("Недостаточно средств для выполнения покупки.")
    except ccxt.AuthenticationError as e:
        logger.error(f"Ошибка аутентификации для пользователя {user_id}: {e}")
        await update.message.reply_text("Ошибка аутентификации. Проверьте свои API-ключи.")
    except ccxt.NetworkError as e:
        logger.error(f"Ошибка сети при покупке для пользователя {user_id}: {e}")
        await update.message.reply_text("Не удалось выполнить покупку из-за сетевой ошибки. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при покупке для пользователя {user_id}: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")