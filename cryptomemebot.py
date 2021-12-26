import logging
import sys
import time

from src.telegram_bot_manager import TelegramBotManager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        tbm = TelegramBotManager()
        tbm.start_polling()
    except Exception as exc:
        logger.error(f"Exception {exc}")
        logger.error(f"Restarting polling in 60s...")
        time.sleep(60)
        tbm = TelegramBotManager()
        tbm.start_polling()
