# menu_ui.py
import logging
import time
from lib.base_observer import BaseObserver  # Provided by your existing code

logger = logging.getLogger(__name__)

class MenuUI(BaseObserver):
    """
    This class is an observer to the OvenWatcher, storing the latest kiln data.
    It also handles screen states and calls KilnDisplay's draw_* methods.
    """

    def __init__(self, display):
        # If you want to identify yourself in logs, pass observer_type to BaseObserver
        super().__init__(observer_type="ui")
        self.display = display
        self.kiln_data = {}

        # Possible screens: "overview", "diagram", "confirm_stop", "confirm_start", "menu", etc.
        self.current_screen = "overview"

        # For advanced menus, you'd track sub-items, indexes, etc.
        self.menu_index = 0

    def send(self, data):
        """
        The OvenWatcher calls this with a dict of kiln data:
          {
            'temperature': <float>,
            'target': <float>,
            'state': "RUNNING"/"IDLE"/etc.,
            'runtime': <seconds>,
            'profile': <str>,
            ...
          }
        We'll store it for reference.
        """
        if not isinstance(data, dict):
            return

        self.kiln_data = data

        # If we're currently on a screen that should update automatically, redraw:
        if self.current_screen == "overview":
            self.display.draw_overview(self.kiln_data)
        elif self.current_screen == "diagram":
            self.display.draw_diagram(self.kiln_data)
        # For other screens (confirm_stop, etc.), we may NOT auto-update.

    def handle_rotary_event(self, event):
        """
        The rotary input calls this with: "rot_left", "rot_right", or "press".
        We decide how to change screens or confirm actions.
        """
        logger.debug(f"[MenuUI] handle_rotary_event: {event}, current_screen={self.current_screen}")

        # Example logic
        if self.current_screen == "overview":
            if event == "rot_left":
                # Go to diagram screen
                self.current_screen = "diagram"
                self.display.draw_diagram(self.kiln_data)
            elif event == "rot_right":
                # Go to confirm_stop screen
                self.current_screen = "confirm_stop"
                self.display.draw_confirm_stop()
            elif event == "press":
                # Possibly show a 'Start Burn' confirm
                self.current_screen = "confirm_start"
                self.display.draw_start_burn()

        elif self.current_screen == "diagram":
            # Maybe rotation does nothing special, or toggles a zoom?
            if event == "press":
                # Press returns to overview
                self.current_screen = "overview"
                self.display.draw_overview(self.kiln_data)

        elif self.current_screen == "confirm_stop":
            # If user presses, we interpret that as "STOP"
            if event == "press":
                logger.info("User confirmed STOP!")
                # You can directly call oven.abort_run() if you have a reference to the oven
                # or send a command to the web UI, etc.
                self.current_screen = "overview"
                self.display.draw_overview(self.kiln_data)
            elif event in ("rot_left", "rot_right"):
                # Maybe you let user toggle Yes/No, up to you
                pass

        elif self.current_screen == "confirm_start":
            if event == "press":
                logger.info("User confirmed START BURN!")
                # e.g. oven.run_profile(...) or a default profile?
                self.current_screen = "overview"
                self.display.draw_overview(self.kiln_data)

        # You can expand to handle other screens:
        # e.g., "menu" for profile selection, etc.
