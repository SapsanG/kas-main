# config/logging_config.py

import logging
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),  # Вывод в консоль
        logging.FileHandler("bot.log", encoding="utf-8")  # Запись в файл с кодировкой UTF-8
    ]
)

# Создаем глобальный логгер
logger = logging.getLogger(__name__)