import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "storage", "settings.json")

DEFAULT_SETTINGS = {
    "temp_scale": "c",
    "last_selected_profile": None,
    "telegram_send_when_idle": False,
}

def _load():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_setting(key, default=None):
    data = _load()
    return data.get(key, DEFAULT_SETTINGS.get(key, default))

def set_setting(key, value):
    data = _load()
    data[key] = value
    _save(data)
