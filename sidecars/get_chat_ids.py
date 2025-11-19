from dotenv import load_dotenv
import os
from telegram import Bot

# Load TELEGRAM_BOT_TOKEN from .env
load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")

bot = Bot(token=token)

me = bot.get_me()
print("Bot username:", me.username)
print("Bot id:", me.id)
print("---------")

# Get recent updates (messages sent TO this bot)
updates = bot.get_updates()

if not updates:
    print("No updates found. Send a message to the bot (or in the group) and run again.")
    raise SystemExit

for u in updates:
    msg = u.message or u.edited_message
    if not msg:
        continue

    chat = msg.chat
    print("Chat type:", chat.type)
    print("Chat id:", chat.id)
    print("Chat title/username:", chat.title or chat.username or "(no title)")
    print("Last text:", msg.text)
    print("---------")
