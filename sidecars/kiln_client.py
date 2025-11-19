"""
kiln_client.py

Shared helper to talk to the kiln-controller via its HTTP + WebSocket API.

Responsibilities:
- Maintain a /status WebSocket loop and call a callback for each state update.
- Provide simple methods to send commands via /api, e.g. run profile, stop.

This module is UI-agnostic: it does not know about Telegram, LCDs etc.
"""

import json
import logging
import time
from typing import Callable, Dict, Optional

import requests
import websocket  # from websocket-client

import sidecar_config as cfg


log = logging.getLogger(__name__)


class KilnClient:
    """
    High-level client for kiln-controller.

    Usage pattern:
      client = KilnClient()
      # in a thread:
      client.run_status_loop(callback)

      # anywhere else:
      client.run_profile_by_name("cone-6-long-glaze")
      client.stop()
    """

    def __init__(self):
        self.ws_status_url: str = cfg.KILN_WS_STATUS
        self.http_base: str = cfg.KILN_HTTP_BASE

    # ------------------------------------------------------------------
    # Status WebSocket
    # ------------------------------------------------------------------

    def run_status_loop(self, callback: Callable[[Dict], None]):
        """
        Connect to /status and call `callback(state_dict)` for each update.

        - This is a blocking loop; run it in a separate thread in your sidecar.
        - Reconnects automatically on error or disconnect.
        - Ignores the initial "backlog" message sent by OvenWatcher.
        """
        while True:
            ws = websocket.WebSocket()
            try:
                log.info("KilnClient: connecting to status WebSocket at %s", self.ws_status_url)
                ws.connect(self.ws_status_url)
                log.info("KilnClient: WebSocket (status) connected.")

                while True:
                    raw = ws.recv()
                    if raw is None:
                        log.warning("KilnClient: WebSocket (status) closed by server.")
                        break

                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        log.debug("KilnClient: ignoring non-JSON message: %r", raw)
                        continue

                    # Ignore backlog; it's for graph history, not needed by all UIs.
                    if isinstance(msg, dict) and msg.get("type") == "backlog":
                        log.debug("KilnClient: received backlog; ignoring.")
                        continue

                    if isinstance(msg, dict):
                        try:
                            callback(msg)
                        except Exception as cb_err:
                            log.error("KilnClient: error in status callback: %s", cb_err)
                    else:
                        log.debug("KilnClient: ignoring non-dict message: %r", msg)

            except Exception as e:
                log.error("KilnClient: error in run_status_loop: %s", e)
                time.sleep(5.0)
            finally:
                try:
                    ws.close()
                except Exception:
                    pass
                time.sleep(1.0)

    # ------------------------------------------------------------------
    # Command helpers via /api
    # ------------------------------------------------------------------

    def _post_api(self, payload: Dict) -> Optional[requests.Response]:
        """
        Internal helper to POST JSON to /api.

        Returns the Response object or None on severe error.
        """
        url = f"{self.http_base}/api"
        try:
            log.info("KilnClient: POST %s payload=%s", url, payload)
            resp = requests.post(url, json=payload, timeout=5)
            log.info("KilnClient: /api returned status %s", resp.status_code)
            return resp
        except Exception as e:
            log.error("KilnClient: /api request failed: %s", e)
            return None

    def run_profile_by_name(self, profile_name: str, startat: int = 0, allow_seek: bool = False):
        """
        Ask the kiln to start a profile by name via the /api endpoint.

        This matches kiln-controller's /api "run" command, which expects:
          { "cmd": "run", "profile": <profile_name>, "startat": <seconds>, "allow_seek": <bool> }
        """
        payload = {
            "cmd": "run",
            "profile": profile_name,
            "startat": startat,
            "allow_seek": allow_seek,
        }
        return self._post_api(payload)

    def stop(self):
        """
        Ask the kiln to stop the current run via /api.

        This matches kiln-controller's /api "stop" command:
          { "cmd": "stop" }
        """
        payload = {"cmd": "stop"}
        return self._post_api(payload)

    # ------------------------------------------------------------------
    # Future extensions (for LCD UI / smarter Telegram)
    # ------------------------------------------------------------------
    #
    # def list_profiles(self):
    #     """List available profiles (via /storage WebSocket or another API)."""
    #     raise NotImplementedError
    #
    # def get_config(self):
    #     """Fetch kiln config (temp units, etc.)."""
    #     raise NotImplementedError
    #
    # We keep these out for now to avoid guessing the exact API shapes.
