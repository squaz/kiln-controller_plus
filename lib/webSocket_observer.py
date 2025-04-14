# --- START OF FILE: lib/webSocket_observer.py ---
import json
import logging # Import logging at the top
from lib.base_observer import BaseObserver

# Get logger for this module
log = logging.getLogger(__name__)

class WebSocketObserver(BaseObserver):
    """
    Observer specifically for sending kiln status updates
    to a connected WebSocket client (wsock).
    """
    def __init__(self, wsock):
        """
        Initializes the observer with the client's WebSocket object.
        Args:
            wsock: The geventwebsocket WebSocket object for the client.
        """
        super().__init__(observer_type="web")
        self.wsock = wsock
        # Log client connection details if available
        client_addr = "Unknown"
        if hasattr(wsock, 'environ') and wsock.environ:
            client_addr = wsock.environ.get('REMOTE_ADDR', 'Unknown')
        log.info(f"WebSocketObserver created for client: {client_addr}")


    def send(self, data):
        """
        Sends data (usually a dictionary) to the connected WebSocket client
        after converting it to a JSON string.

        IMPORTANT: This method now RAISES exceptions if the send fails
                   (e.g., socket closed), allowing the caller (OvenWatcher)
                   to detect the failure and remove the observer.
        Args:
            data: The dictionary containing the status update.

        Raises:
            WebSocketError: Or other underlying socket errors if the send fails.
        """
        # The caller (OvenWatcher.notify_all) is responsible for handling exceptions
        # during the send operation and removing the observer if necessary.
        if self.wsock: # Check if socket still exists (basic check)
            # log.debug(f"Sending to {self.wsock.environ.get('REMOTE_ADDR', 'ws')}: {data}") # Optional: Debug log
            self.wsock.send(json.dumps(data))
        else:
            # This case should ideally not be reached if OvenWatcher removes observer promptly
            log.warning("WebSocketObserver attempted send, but wsock is None.")
# --- END OF FILE: lib/webSocket_observer.py ---