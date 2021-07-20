import logging
import os
import sys
import pytz

from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, JobQueue

import config
from reddit_meme_farmer import RedditMemeFarmer
from datetime import time
from spongebobcase import tospongebob
import random

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer


class TelegramBotManager(RedditMemeFarmer):
    def __init__(self, group=True):
        super().__init__()
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # create the updater, that will automatically create also a dispatcher and a queue to
        # make them dialogue

        if group:
            self._chat_id = config.TELEGRAM_GROUP_CHAT_ID
        else:
            self._chat_id = config.TELEGRAM_CHAT_ID

        self._updater = Updater(token=config.TELEGRAM_TOKEN, use_context=True)
        self.dispatcher = self._updater.dispatcher

        # add handlers for start and help commands
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("help", self.help))
        self.dispatcher.add_handler(CommandHandler("meme", self.send_meme))
        self.dispatcher.add_handler(CommandHandler("dailymeme", self.daily_meme_start))
        self.dispatcher.add_handler(CommandHandler("dailymemestop", self.daily_meme_stop))
        self.dispatcher.add_handler(CommandHandler("conversationstart", self.chatbot_start))
        self.dispatcher.add_handler(CommandHandler("conversationstop", self.chatbot_stop))

        # add an handler for normal text (not commands)
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.text))

        # add an handler for errors
        self.dispatcher.add_error_handler(self.error)

        bot_name, bot_username = self._updater.bot.get_me()["first_name"], self._updater.bot.get_me()["username"]
        startup_text = f'{bot_name} (@{bot_username}) is now running using Telegram' \
                       f' {"group" if group else "personal"} chat id'
        self.logger.info(startup_text)

        # set up variables
        self.chatbot = ChatBot("CryptoMemeBot")
        self.chatbot_state = False

    def send_message(self, message: str) -> Message:
        return self._updater.bot.send_message(self._chat_id, text=message)

    def send_photo(self, image_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_photo(self._chat_id, photo=open(image_path, "rb"), caption=caption)

    def send_video(self, video_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_video(self._chat_id, video=open(video_path, "rb"), supports_streaming=True,
                                            caption=caption)

    def send_animation(self, animation_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_animation(self._chat_id, animation=open(animation_path, "rb"), caption=caption)

    def send_captioned_media(self, filepath: str) -> bool:
        """ The filepath consists of the full path, name of the file and the extension."""
        filename, ext = os.path.splitext(os.path.basename(filepath))

        if ext == ".jpg" or ext == ".png":
            self.send_photo(filepath, caption=filename)
        elif ext == ".gif":
            self.send_animation(filepath, caption=filename)
        elif ext == ".mp4":
            self.send_video(filepath, caption=filename)
        else:
            self.logger.warning(f"Unrecognized extension '{ext}' in '{filepath}'")
            return False
        self.logger.info(f"Sent {filepath} to Telegram chat")
        return True

    # function to handle the /start command
    @staticmethod
    def start(update: Update, _: CallbackContext):
        update.message.reply_text('Start command received')

    # function to handle the /help command
    def help(self, update: Update, _: CallbackContext):
        msg = "The following commands are available:\n" \
              "/meme: Fetch a dank meme\n" \
              "/dailymeme: Fetch a meme daily at 9:30 AM\n" \
              "/dailymemestop: Stop fetching daily memes\n" \
              "/conversationstart: Start talking with a trained chat bot\n" \
              "/conversationstop: Stop the chat bot\n" \
              "/help: This help page"
        self.send_message(msg)

    # function to handle errors occurred in the dispatcher
    @staticmethod
    def error(update: Update, context: CallbackContext):
        update.message.reply_text(f'An error occurred: {context.error}')

    def _send_meme_daily(self, context: CallbackContext):
        filepath = RedditMemeFarmer.get_crypto_meme_path(self)
        filename, ext = os.path.splitext(os.path.basename(filepath))

        if ext == ".jpg" or ext == ".png":
            context.bot.send_photo(chat_id=context.job.context, photo=open(filepath, "rb"), caption=filename)
        elif ext == ".gif":
            context.bot.send_animation(chat_id=context.job.context, amnimation=open(filepath, "rb"), caption=filename)
        elif ext == ".mp4":
            context.bot.send_video(chat_id=context.job.context, video=open(filepath, "rb"),
                                   supports_streaming=True, caption=filename)

    def send_meme(self, update: Update, _: CallbackContext):
        update.message.reply_text(f'Fetching a dank meme, just for you...')
        filepath = RedditMemeFarmer.get_crypto_meme_path(self)
        self.send_captioned_media(filepath)

    def daily_meme_start(self, update: Update, context: CallbackContext):
        daily_meme_time = time(hour=9, minute=30, second=00, tzinfo=pytz.timezone('Europe/Vienna'))
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Daily meme has been set! You'll be sent a meme at "
                                            f"{daily_meme_time.strftime('%H:%M')} daily")
        context.job_queue.run_daily(self._send_meme_daily, context=update.message.chat_id,
                                    days=(0, 1, 2, 3, 4, 5, 6), time=daily_meme_time)

    def daily_meme_stop(self, update: Update, context: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Daily meme stopped")
        context.job_queue.stop()

    def chatbot_start(self, update: Update, context: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Starting and training chatbot in English")
        # Create a new trainer for the chatbot
        trainer = ChatterBotCorpusTrainer(self.chatbot)

        # Train the chatbot based on the english corpus
        trainer.train("chatterbot.corpus.english")

        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Training complete, chatbot is ready!")

        self.chatbot_state = True

    def chatbot_stop(self, update: Update, context: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Chatbot stopped")
        self.chatbot_state = False

    # function to handle normal text
    def text(self, update: Update, context: CallbackContext):
        msg_text = update.message.text
        antagonistics = ["annoying", "sad", "boring", "poor"]

        if not self.chatbot_state:
            if "bad bot" in msg_text.lower():
                responses = ["I'm sorry, I will try harder next time 😭", "But please sir, I am but a mere bot...😓"]
                update.message.reply_text(random.choice(responses))
            if "good bot" in msg_text.lower():
                responses = ["Woohoo, I aim to please 😊", f"Thank you very much {update.effective_user}! 😉"]
                update.message.reply_text(random.choice(responses))
            if any(antagonistic in msg_text.lower() for antagonistic in antagonistics):
                update.message.reply_text(tospongebob(msg_text))
        else:
            response = self.chatbot.get_response(msg_text).text
            update.message.reply_text(response)

    def start_polling(self):
        # start your shiny new bot
        self._updater.start_polling()

        # run the bot until Ctrl-C
        self._updater.idle()

    def exit(self):
        try:
            self.logger.info("Stopping telegram bot...")
            self._updater.stop()
            self.logger.info("Telegram bot stopped successfully")
        except:
            self.logger.info("Failed to shutdown telegram bot. Please make sure it is correctly terminated")


if __name__ == '__main__':
    tbm = TelegramBotManager()
    tbm.start_polling()
