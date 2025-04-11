from telegram import Update
from telegram.ext import ContextTypes
import logging
from app.shared import bot_state_manager, get_user_context
from app.trading_logic import start_trading
from config.logging_config import logger
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)



# Команда /autobuy
async def autobuy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /autobuy вызвана пользователем {user_id}")
    
    # Получаем контекст пользователя
    user_context = get_user_context(user_id)
    
    if bot_state_manager.is_trading_active(user_id):
        await update.message.reply_text('Автоматическая торговля уже запущена. Чтобы остановить, используйте команду /stop.')
        return
    
    symbol = "KAS/USDT"
    bot_state_manager.start(user_id)  # Отмечаем, что торговля запущена для пользователя
    
    # Запускаем асинхронную торговлю с передачей update
    asyncio.create_task(start_trading(symbol, update))
    await update.message.reply_text(f'Автоматическая торговля запущена для {symbol}. Чтобы остановить, используйте команду /stop.')

# Команда /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logger.info(f"Команда /stop вызвана пользователем {user_id}")
    
    if not bot_state_manager.is_trading_active(user_id):
        await update.message.reply_text('Автоматическая торговля не запущена.')
        return
    
    bot_state_manager.stop(user_id)
    await update.message.reply_text('Автоматическая торговля остановлена.')
