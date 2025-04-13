# menu_ui.py
import logging
from lib.base_observer import BaseObserver
from display_ui.screens import build_screens

logger = logging.getLogger(__name__)

class MenuUI(BaseObserver):
    """
    Handles screen state and input navigation.
    Receives kiln data via .send() and forwards it to the active screen.
    Implements global navigation logic for tab-based and submenu screens.
    """
    def __init__(self, display):
        super().__init__(observer_type="ui")
        self.display = display
        self.kiln_data = {}

        # Build and store all screen instances
        self.screens = build_screens(display, self)

        self.current_tab_index = 0
        self.in_submenu = False

        # Start with first tab
        self.screen_name = "overview"
        self.screen = self.screens[self.screen_name]
        if hasattr(self.screen, "on_enter"):
            self.screen.on_enter()

    def get_allowed_tabs(self):
        """Return tab list depending on kiln state."""
        state = self.kiln_data.get("state", "IDLE").upper()
        if state in {"RUNNING", "PAUSED"}:
            return ["overview", "diagram"]
        else:
            return [
                "overview",
                "diagram",
                "profile_selector",
                "manual_control",
                "profile_builder",
                "settings",
                "overview"  # fallback
            ]

    def send(self, data):
        if not isinstance(data, dict):
            return
        self.kiln_data = data
        if hasattr(self.screen, "update"):
            self.screen.update(self.kiln_data)

    def handle_rotary_event(self, event):
        logger.debug(f"[MenuUI] rotary event: {event} on screen: {self.screen_name}")

        if self.in_submenu:
            if hasattr(self.screen, "handle_event"):
                result = self.screen.handle_event(event)
                if result == "tab_bar":
                    self.enter_tab_bar()
                elif isinstance(result, str):
                    self.switch_to(result)

        else:
            tabs = self.get_allowed_tabs()

            if event == "rot_left":
                self.current_tab_index = (self.current_tab_index - 1) % len(tabs)
                self.switch_to(tabs[self.current_tab_index])
            elif event == "rot_right":
                self.current_tab_index = (self.current_tab_index + 1) % len(tabs)
                self.switch_to(tabs[self.current_tab_index])
            elif event == "short_press":
                if hasattr(self.screen, "handle_event"):
                    result = self.screen.handle_event("short_press")
                    if result != "tab_bar":
                        self.in_submenu = True
            elif event == "long_press":
                self.current_tab_index = 0
                self.switch_to("overview")

    def switch_to(self, new_screen_name):
        if new_screen_name is None or new_screen_name == self.screen_name:
            return
        if new_screen_name not in self.screens:
            logger.warning(f"[MenuUI] Tried to switch to unknown screen: {new_screen_name}")
            return

        logger.info(f"[MenuUI] Switching to screen: {new_screen_name}")
        self.screen_name = new_screen_name
        self.screen = self.screens[new_screen_name]
        if hasattr(self.screen, "on_enter"):
            self.screen.on_enter()

    def enter_tab_bar(self):
        self.in_submenu = False
        tabs = self.get_allowed_tabs()
        self.switch_to(tabs[self.current_tab_index])
