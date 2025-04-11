import logging
import telegram
import config
from lib.base_observer import BaseObserver
import time

log = logging.getLogger(__name__)

class TelegramObserver(BaseObserver):
    def __init__(self):
        super().__init__(observer_type="telegram")
        self.enabled = config.enable_telegram_observer
        self.token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.interval = config.telegram_update_interval
        self.bot = None
        self.last_sent = 0

        if not self.enabled:
            log.info("[TelegramObserver] Disabled in config.")
            return

        try:
            self.bot = telegram.Bot(token=self.token)
            log.info("[TelegramObserver] Bot initialized successfully.")
        except Exception as e:
            log.error(f"[TelegramObserver] Initialization failed: {e}")
            self.enabled = False

    def send(self, data):
        if not self.enabled or not self.bot:
            return
        
        #to avoid backlog which is not in the correct format
        #TODO implement backlog for telegram bot.
        if not isinstance(data, dict):
            log.debug(f"[TelegramObserver] Ignoring non-dict message: {data}")
            return
    
        # Skip if state is IDLE and we're not supposed to send in that case
        state = data.get("state", "IDLE")
        if state == "IDLE" and not config.telegram_send_when_idle:
            log.debug("[TelegramObserver] Skipping message while kiln is IDLE.")
            return


        now = time.time()
        if now - self.last_sent < self.interval:
            return  # Throttle messages

        try:
            message = self.format_message(data)
            self.bot.send_message(chat_id=self.chat_id, text=message)
            self.last_sent = now
        except Exception as e:
            log.error(f"[TelegramObserver] Failed to send message: {e}")

    def format_message(self, data):
        temp = data.get("temperature", 0.0)
        target = data.get("target", 0.0)
        state = data.get("state", "IDLE")
        profile = data.get("profile", "N/A")
        runtime = int(data.get("runtime", 0))
        err = data.get("pidstats", {}).get("err", 0.0)

        return (
            f"🔥 Kiln Status Update 🔥\n"
            f"State: {state}\n"
            f"Profile: {profile}\n"
            f"Temp: {temp:.1f}°C / Target: {target:.1f}°C\n"
            f"Runtime: {runtime}s\n"
            f"Error: {err:+.1f}°C"
        )
