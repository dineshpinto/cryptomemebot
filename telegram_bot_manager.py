import html
import json
import logging
import os
import random
import sys
import traceback
from datetime import time

import pytz
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from spongebobcase import tospongebob
from telegram import Update, Message, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, Job

import config
from reddit_meme_farmer import RedditMemeFarmer


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
        self.dispatcher.add_handler(CommandHandler("meme", self.get_meme))
        self.dispatcher.add_handler(CommandHandler("dailymeme", self.daily_meme_start))
        self.dispatcher.add_handler(CommandHandler("dailymemestop", self.daily_meme_stop))
        self.dispatcher.add_handler(CommandHandler("conversationstart", self.chatbot_start))
        self.dispatcher.add_handler(CommandHandler("conversationstop", self.chatbot_stop))

        # add an handler for normal text (not commands)
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.text))

        # add an handler for errors
        self.dispatcher.add_error_handler(self.error_handler)

        bot_name, bot_username = self._updater.bot.get_me()["first_name"], self._updater.bot.get_me()["username"]
        startup_text = f'{bot_name} (@{bot_username}) is now running using Telegram' \
                       f' {"group" if group else "personal"} chat id'
        self.logger.info(startup_text)

        # set up variables
        self.chatbot = ChatBot("CryptoMemeBot")
        self.chatbot_on = False

    def send_message(self, message: str) -> Message:
        return self._updater.bot.send_message(self._chat_id, text=message)

    def send_photo(self, image_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_photo(self._chat_id, photo=open(image_path, "rb"), caption=caption)

    def send_video(self, video_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_video(self._chat_id, video=open(video_path, "rb"), supports_streaming=True,
                                            caption=caption)

    def send_animation(self, animation_path: str, caption: str = None) -> Message:
        return self._updater.bot.send_animation(self._chat_id, animation=open(animation_path, "rb"), caption=caption)

    # function to handle the /start command
    @staticmethod
    def start(update: Update, _: CallbackContext):
        update.message.reply_text('Start command received')

    # function to handle the /help command
    @staticmethod
    def help(update: Update, _: CallbackContext):
        msg = "The following commands are available:\n" \
              "/meme: Fetch a dank meme\n" \
              "/dailymeme: Fetch a meme daily at 9:30 AM\n" \
              "/dailymemestop: Stop fetching daily memes\n" \
              "/conversationstart: Start talking with a trained chat bot\n" \
              "/conversationstop: Stop the chat bot\n" \
              "/help: This help page"
        update.message.reply_text(msg)

    # function to handle errors occurred in the dispatcher
    def error_handler(self, update: object, context: CallbackContext):
        context.bot.send_message(chat_id=self._chat_id, text=f'An error occurred: {context.error}')
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error(msg="Exception while handling an update:", exc_info=context.error)

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f'An exception was raised while handling an update\n'
            f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
            '</pre>\n\n'
            f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
            f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
            f'<pre>{html.escape(tb_string)}</pre>'
        )

        # Finally, send the message
        context.bot.send_message(chat_id=self._chat_id, text=message, parse_mode=ParseMode.HTML)

    def _send_meme(self, context: CallbackContext):
        filepath = RedditMemeFarmer.get_crypto_meme_path(self)
        filename, ext = os.path.splitext(os.path.basename(filepath))

        # Check if function is called by a Job or directly, and set chat id accordingly
        if isinstance(context.job, Job):
            chat_id = context.job.context
        else:
            chat_id = self._chat_id

        if ext == ".jpg" or ext == ".png":
            context.bot.send_photo(chat_id=chat_id, photo=open(filepath, "rb"), caption=filename)
        elif ext == ".gif":
            context.bot.send_animation(chat_id=chat_id, amnimation=open(filepath, "rb"), caption=filename)
        elif ext == ".mp4":
            context.bot.send_video(chat_id=chat_id, video=open(filepath, "rb"),
                                   supports_streaming=True, caption=filename)
        else:
            text = f"Unknown file extension '{ext}' in filepath"
            context.bot.send_message(chat_id=chat_id, text=text)
            self.logger.warning(text)

    def get_meme(self, update: Update, context: CallbackContext):
        update.message.reply_text(f'Fetching a dank meme, just for you...')
        self._send_meme(context)

    def daily_meme_start(self, update: Update, context: CallbackContext):
        daily_meme_time = time(hour=9, minute=30, second=00, tzinfo=pytz.timezone('Europe/Vienna'))
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Daily meme has been set! You'll be sent a meme at "
                                            f"{daily_meme_time.strftime('%H:%M')} daily")
        context.job_queue.run_daily(self._send_meme, context=update.message.chat_id,
                                    days=(0, 1, 2, 3, 4, 5, 6), time=daily_meme_time)

    def daily_meme_stop(self, update: Update, context: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Daily meme stopped")
        context.job_queue.stop()

    def chatbot_start(self, update: Update, _: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Starting and training chatbot in English")
        # Create a new trainer for the chatbot
        trainer = ChatterBotCorpusTrainer(self.chatbot)

        # Train the chatbot based on the english corpus
        trainer.train("chatterbot.corpus.english")

        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Training complete, chatbot is ready!")

        self.chatbot_on = True

    def chatbot_stop(self, update: Update, _: CallbackContext):
        self._updater.bot.send_message(chat_id=update.message.chat_id,
                                       text="Chatbot stopped")
        self.chatbot_on = False

    # function to handle normal text
    def text(self, update: Update, _: CallbackContext):
        msg_text = update.message.text
        antagonistics = ["annoying", "sad", "boring", "poor"]

        if not self.chatbot_on:
            if "bad bot" in msg_text.lower():
                responses = [
                    f"I'm sorry {update.effective_user.first_name}, I will try harder next time 😭",
                    f"But please {update.effective_user.first_name}, I am but a mere bot...😓"
                ]
                update.message.reply_text(random.choice(responses))
            if "good bot" in msg_text.lower():
                responses = [
                    f"Woohoo, thanks {update.effective_user.first_name}, I aim to please 😊",
                    f"Thank you very much {update.effective_user.first_name}! 😉"
                ]
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

    def exit(self, update: Update, _: CallbackContext):
        try:
            text = f'Shutting down bot'
            self.logger.info(text)
            update.message.reply_text(text)
            self._updater.stop()
        except Exception as exc:
            text = "Failed to shut down bot"
            update.message.reply_text(text + f"{exc}")
            self.logger.warning(text + f"{exc}")
        else:
            text = "Bot stopped successfully"
            update.message.reply_text(text)
            self.logger.info(text)


if __name__ == '__main__':
    tbm = TelegramBotManager()
    tbm.start_polling()
