import json
from lib.base_observer import BaseObserver

class WebSocketObserver(BaseObserver):
    def __init__(self, wsock):
        super().__init__(observer_type="web")
        self.wsock = wsock

    def send(self, data):
        try:
            self.wsock.send(json.dumps(data))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[WebSocketObserver] send() failed: {e}")
