# profile_builder_screen.py
import logging
from display_ui.screens.screen_base import UIScreen

logger = logging.getLogger(__name__)

class ProfileBuilderScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)

    def on_enter(self):
        """Called when switching to this screen in tab mode."""
        self.draw(mode="tab_bar")


    def enter_screen(self):
         """Called by MenuUI on short press when at level 0."""
         self.draw(mode="submenu") # Show the WIP message full screen
         return "enter_submenu" # Enter level 1 to show the message

    def draw(self, mode="tab_bar"):
        # Tab bar drawing is handled by MenuUI calling TabBar component
        pass # Do nothing here

        # --- Full Screen WIP Message ---
        lines = [
            "Profile Builder",
            "",
            "Work In Progress...",
            "Editing profiles will",
            "be available later.",
            "Hold: Back"
        ]
        self.display.draw_lines(lines)

    def handle_event(self, event):
        """Handles events when screen is active (level > 0)."""
        # Short press does nothing here.
        # Long press is handled globally to go back.
        pass

    def update(self, data):
         """Update based on kiln data."""
         if self.ui.current_screen_name == "profile_builder" and self.ui.current_screen_level == 0:
             self.draw(mode="tab_bar")

    def on_exit(self):
        logger.debug("[ProfileBuilderScreen] Exited.")

