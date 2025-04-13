# --- START OF FILE: display_ui/screens/component_screens/tab_bar.py ---
import logging

logger = logging.getLogger(__name__)

class TabBar:
    # ... (__init__ remains the same) ...
    def __init__(self, ui_manager):
        self.ui = ui_manager; self.display = ui_manager.display
        self.tab_display_names = { "overview": "Overview", "diagram": "Diagram", "profile_selector": "Profiles", "manual_control": "Manual", "profile_builder": "Builder", "settings": "Settings" }
        self.submenu_tabs = {"profile_selector", "manual_control", "profile_builder", "settings"}

    def draw(self):
        """Draws the tab bar onto the display buffer."""
        logger.info("[TabBar] Drawing tab bar view.") # Add log
        if not self.display: logger.error("[TabBar] Display not available."); return

        lines = []; lines.append(f"── State: {self.ui.kiln_data.get('state', 'IDLE').upper()} ──"); lines.append("")
        allowed_tabs = self.ui.get_allowed_tabs(); current_tab_key = self.ui.current_screen_name
        max_tabs_to_show = min(6, self.display.rows - 2); tabs_to_display = allowed_tabs[:max_tabs_to_show]

        for tab_key in tabs_to_display:
            display_name = self.tab_display_names.get(tab_key, tab_key.capitalize())
            prefix = "▶" if tab_key == current_tab_key else " "
            suffix = " ▶" if tab_key in self.submenu_tabs else ""
            lines.append(f"{prefix} [{display_name}{suffix}]")

        while len(lines) < self.display.rows: lines.append("")
        self.display.draw_lines(lines, clear_first=True)

# --- END OF FILE: display_ui/screens/component_screens/tab_bar.py ---