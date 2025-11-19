#!/usr/bin/env python3
"""
kiln_telegram_bot.py

Telegram sidecar for kiln-controller.

Uses:
- KilnClient (kiln_client.py) to receive /status updates and send commands via /api.
- watch_kiln_errors (kiln_errors.py) to receive WARN/ERROR lines from journald.

This version is designed for python-telegram-bot v13.x (synchronous).
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Tuple

from telegram import Bot  # python-telegram-bot==13.1
# NOTE: no async/await here; v13 is sync API.

import sidecar_config as cfg
from kiln_client import KilnClient
from kiln_errors import watch_kiln_errors


log = logging.getLogger(__name__)


class TelegramSender:
    """
    Handles all Telegram sending logic:

    - Init Bot with token / chat IDs.
    - Throttle regular status messages.
    - Throttle & deduplicate error messages.
    - Log successes / failures.
    """

    def __init__(self):
        self.enabled: bool = cfg.TELEGRAM_ENABLED
        self.token: str = cfg.TELEGRAM_BOT_TOKEN
        self.chat_ids: List[int] = cfg.TELEGRAM_CHAT_IDS

        self.status_interval: int = cfg.TELEGRAM_UPDATE_INTERVAL
        self.send_when_idle: bool = cfg.TELEGRAM_SEND_WHEN_IDLE

        self.send_errors: bool = cfg.TELEGRAM_SEND_ERRORS
        self.error_throttle: int = cfg.TELEGRAM_ERROR_THROTTLE
        self.error_dedup_window: int = cfg.TELEGRAM_ERROR_DEDUP_WINDOW

        self.bot: Optional[Bot] = None
        self.last_status_sent: float = 0.0
        self.last_error_sent: float = 0.0
        self.recent_errors: List[Tuple[float, str]] = []  # (timestamp, message)

        self._lock = threading.Lock()

        if not self.enabled:
            log.info("[TelegramSender] Disabled in sidecar_config.")
            return

        if not self.token:
            log.error("[TelegramSender] TELEGRAM_BOT_TOKEN is empty. Disabling Telegram.")
            self.enabled = False
            return

        if not self.chat_ids:
            log.error("[TelegramSender] No TELEGRAM_CHAT_IDS configured. Disabling Telegram.")
            self.enabled = False
            return

        try:
            self.bot = Bot(token=self.token)
            log.info(
                "[TelegramSender] Bot initialized with %d chat ID(s).",
                len(self.chat_ids),
            )
        except Exception as e:
            log.error("[TelegramSender] Bot initialization failed: %s", e)
            self.enabled = False

    # ------------------------------------------------------------------
    # Public API for loops
    # ------------------------------------------------------------------

    def handle_status(self, data: Dict):
        """
        Callback for KilnClient.run_status_loop(state_dict).

        - Skips when disabled or bot not ready.
        - Optionally skips while kiln is IDLE.
        - Throttles using TELEGRAM_UPDATE_INTERVAL.
        """
        if not self.enabled or not self.bot:
            return

        if not isinstance(data, dict):
            return

        state = data.get("state", "IDLE")
        if state == "IDLE" and not self.send_when_idle:
            log.debug("[TelegramSender] Skipping status while kiln is IDLE.")
            return

        now = time.time()
        if now - self.last_status_sent < self.status_interval:
            log.debug("[TelegramSender] Skipping status due to interval throttle.")
            return

        message = self._format_status_message(data)
        self._send_to_all(message, context="status")
        self.last_status_sent = now

    def handle_error_line(self, line: str):
        """
        Callback for watch_kiln_errors(line).

        - Skips if Telegram/errors disabled.
        - Throttles using TELEGRAM_ERROR_THROTTLE.
        - Deduplicates identical lines in a time window.
        """
        if not self.enabled or not self.bot or not self.send_errors:
            return

        now = time.time()
        if now - self.last_error_sent < self.error_throttle:
            log.debug("[TelegramSender] Skipping error due to throttle.")
            return

        self._prune_old_errors(now)

        if any(line == msg for (_t, msg) in self.recent_errors):
            log.debug("[TelegramSender] Skipping duplicate error line.")
            return

        short_line = line.strip()
        if len(short_line) > 400:
            short_line = short_line[:397] + "..."

        message = f"⚠️ Kiln Error\n\n{short_line}"
        self._send_to_all(message, context="error")
        self.last_error_sent = now
        self.recent_errors.append((now, line))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_to_all(self, text: str, context: str = "unknown"):
        """
        Send messages to all chat_ids in a thread-safe way.
        Logs success/failure for debugging.
        """
        if not self.enabled or not self.bot:
            return

        with self._lock:
            for chat_id in self.chat_ids:
                try:
                    self.bot.send_message(chat_id=chat_id, text=text)
                    log.info(
                        "[TelegramSender] Sent %s message to chat_id=%s",
                        context,
                        chat_id,
                    )
                except Exception as e:
                    log.error(
                        "[TelegramSender] Failed to send %s message to chat_id=%s: %s",
                        context,
                        chat_id,
                        e,
                    )

    def _format_status_message(self, data: Dict) -> str:
        """
        Build a human-readable status message from kiln state dict.
        """

        temp = data.get("temperature")
        target = data.get("target")
        state = data.get("state", "UNKNOWN")
        runtime = int(data.get("runtime", 0))
        totaltime = int(data.get("totaltime", 0))
        heat = data.get("heat", 0.0)

        pidstats = data.get("pidstats") or {}
        err = pidstats.get("err")

        profile_name = data.get("profile", "N/A")

        def fmt_temp(v):
            if isinstance(v, (int, float)):
                return f"{v:.1f}°C"
            return "n/a"

        def fmt_err(v):
            if isinstance(v, (int, float)):
                return f"{v:+.1f}°C"
            return "n/a"

        def fmt_seconds(sec: int) -> str:
            hours = sec // 3600
            minutes = (sec % 3600) // 60
            seconds = sec % 60
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"

        temp_str = fmt_temp(temp)
        target_str = fmt_temp(target)
        err_str = fmt_err(err)
        runtime_str = fmt_seconds(runtime)
        totaltime_str = fmt_seconds(totaltime)

        heat_str = "off"
        if isinstance(heat, (int, float)) and heat > 0:
            heat_str = "on"

        lines = [
            "🔥 Kiln Status Update 🔥",
            f"State: {state}",
            f"Profile: {profile_name}",
            f"Temp: {temp_str} / Target: {target_str}",
            f"Runtime: {runtime_str} / Total: {totaltime_str}",
            f"Heat: {heat_str}",
            f"PID error: {err_str}",
        ]
        return "\n".join(lines)

    def _prune_old_errors(self, now: float):
        cutoff = now - self.error_dedup_window
        self.recent_errors = [
            (t, msg) for (t, msg) in self.recent_errors if t >= cutoff
        ]


def main():
    # Sidecar logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    log.info("Starting kiln Telegram sidecar (using KilnClient + kiln_errors).")

    sender = TelegramSender()
    if not sender.enabled:
        log.warning("TelegramSender is disabled; exiting sidecar.")
        return

    client = KilnClient()

    # Status loop thread
    status_thread = threading.Thread(
        target=client.run_status_loop,
        args=(sender.handle_status,),
        daemon=True,
    )
    status_thread.start()

    # Journal error loop thread
    journal_thread = threading.Thread(
        target=watch_kiln_errors,
        args=(sender.handle_error_line,),
        daemon=True,
    )
    journal_thread.start()

    # In the future: we can also add a simple Telegram command handler here
    # that uses `client.run_profile_by_name()` and `client.stop()` for
    # special users / commands.

    try:
        while True:
            time.sleep(60.0)
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt received. Shutting down Telegram sidecar.")


if __name__ == "__main__":
    main()
