# --- START OF FILE: display_ui/screens/settings_screen.py ---
import logging
from display_ui.screens.screen_base import UIScreen
from display_ui.screens.component_screens.scrollable_list import ScrollableList

logger = logging.getLogger(__name__)

class SettingsScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.options = ["WiFi Config (F)", "General Settings (F)", "[ Return ]"]
        self.list_component = None

    def on_enter(self):
        pass # Draw handled by MenuUI

    def enter_screen(self):
        def on_select(selected_index, selected_item):
            logger.debug(f"Settings item selected: {selected_item}")
            if selected_item == "[ Return ]":
                self.ui.pop_context()
            elif selected_item == "WiFi Config (F)":
                logger.info("WiFi Config selected (Not Implemented)")
                self._show_wip_message()
            elif selected_item == "General Settings (F)":
                 logger.info("General Settings selected (Not Implemented)")
                 self._show_wip_message()
            else:
                self.ui.pop_context()

        def on_cancel():
            self.ui.pop_context()

        # --- FIX: Pass visible_count ---
        calculated_visible_count = max(1, self.display.rows - 1) if self.display and hasattr(self.display, 'rows') else 4

        self.list_component = ScrollableList(
            ui_manager=self.ui,
            items=self.options,
            visible_count=calculated_visible_count, # <-- UNCOMMENTED THIS LINE
            title="Settings:",
            initial_selection=0,
            on_select_callback=on_select,
            on_cancel_callback=on_cancel
        )
        # --- END FIX ---

        self.ui.push_context(
            mode="scrollable_list", component=self.list_component, caller_screen_name="settings"
        )
        return "context_pushed"

    def _show_wip_message(self):
         confirm_screen = self.ui.screens.get("confirm")
         if not confirm_screen: return
         def okay_action(): self.ui.pop_context()
         confirm_screen.set_context("Feature not yet implemented.", okay_action, okay_action)
         self.ui.push_context(mode="confirm", component=confirm_screen, caller_screen_name="settings")

    def draw(self, mode="tab_bar"):
        # --- Add Standardized Tab Bar Drawing ---
        if not self.display: return
        lines = []
        if mode == "tab_bar":
            # Tab bar drawing is handled by MenuUI calling TabBar component
            pass # Do nothing here
        else:
             lines.append("Settings")
             lines.append("")
             lines.append("(Loading...)")
        while len(lines) < self.display.rows: lines.append("")
        self.display.draw_lines(lines, clear_first=True)
        # --- End Standardized Tab Bar ---

    def handle_event(self, event):
        logger.debug(f"[SettingsScreen] handle_event({event}) called unexpectedly at level {self.ui.current_screen_level}")
        if event == "short_press" or event == "long_press":
             self.ui.pop_context_or_level()

    def update(self, data):
        if self.ui.current_screen_name == "settings" and self.ui.current_screen_level == 0:
             if self.last_kiln_data.get('state') != data.get('state'):
                  self.ui.redraw_current_view()
                  self.last_kiln_data = data.copy()

    def on_exit(self):
         self.list_component = None
         logger.debug("[SettingsScreen] Exited.")

# --- END OF FILE: display_ui/screens/settings_screen.py ---