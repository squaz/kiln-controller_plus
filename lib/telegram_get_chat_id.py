import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=telegram_bot_token)
updates = bot.get_updates()

for update in updates:
    print(update.message.chat.id)
