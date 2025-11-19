# sidecar_config.py (add or verify these parts)

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Kiln / network settings
# ---------------------------------------------------------------------------

KILN_HOST = "localhost"
KILN_PORT = 8081

KILN_WS_STATUS = f"ws://{KILN_HOST}:{KILN_PORT}/status"
KILN_WS_CONTROL = f"ws://{KILN_HOST}:{KILN_PORT}/control"

# Base HTTP URL, for /api calls etc.
KILN_HTTP_BASE = f"http://{KILN_HOST}:{KILN_PORT}"

# systemd unit + journal filter
JOURNAL_UNIT = "kiln-controller.service"
KILN_JOURNAL_FILTER_REGEX = r"(INFO|WARN|ERROR).* (oven|kiln-controller|gevent)"

# ---------------------------------------------------------------------------
# Telegram secrets (from .env)
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_raw_chat_ids = os.getenv("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = []
for part in _raw_chat_ids.split(","):
    part = part.strip()
    if not part:
        continue
    try:
        TELEGRAM_CHAT_IDS.append(int(part))
    except ValueError:
        pass

# ---------------------------------------------------------------------------
# Telegram behavior (edit here, not in .env)
# ---------------------------------------------------------------------------

TELEGRAM_ENABLED = True
TELEGRAM_UPDATE_INTERVAL = 30
TELEGRAM_SEND_WHEN_IDLE = True
TELEGRAM_SEND_ERRORS = True
TELEGRAM_ERROR_THROTTLE = 30
TELEGRAM_ERROR_DEDUP_WINDOW = 300
