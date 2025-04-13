# --- START OF FILE: display_ui/screens/profile_selector_screen.py ---
import os
import json
import logging
from display_ui.screens.screen_base import UIScreen
from display_ui.screens.component_screens.scrollable_list import ScrollableList
import settings_manager
import config

logger = logging.getLogger(__name__)

class ProfileSelectorScreen(UIScreen):
    # ... (__init__, on_enter, enter_screen, load_profiles remain the same as previous version) ...
    def __init__(self, ui): super().__init__(ui); self.profiles = []; self.list_component = None
    def on_enter(self): pass
    def enter_screen(self):
        self.load_profiles(); initial_selection_index = 0
        last_profile_file = getattr(config, 'last_selected_profile', None)
        if last_profile_file:
            for i, (filename, _) in enumerate(self.profiles):
                if filename == last_profile_file: initial_selection_index = i; break
        list_items = [name for _, name in self.profiles] if self.profiles else ["(No Profiles Found)"]
        list_items.append("[ Return ]")
        def on_select(selected_index, selected_item):
            if selected_item == "[ Return ]" or selected_item == "(No Profiles Found)": self.ui.pop_context()
            elif selected_index < len(self.profiles): self._show_confirmation(self.profiles[selected_index][0], self.profiles[selected_index][1])
            else: logger.warning(f"Invalid selection index: {selected_index}"); self.ui.pop_context()
        def on_cancel(): logger.debug("[ProfileSelector] List cancelled."); self.ui.pop_context()
        calculated_visible_count = max(1, self.display.rows - 1) if self.display and hasattr(self.display, 'rows') else 4
        self.list_component = ScrollableList(self.ui, list_items, calculated_visible_count, "Select Profile:", initial_selection_index, on_select, on_cancel)
        self.ui.push_context("scrollable_list", self.list_component, "profile_selector")
        return "context_pushed"
    def load_profiles(self):
        script_dir = os.path.dirname(__file__); project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
        storage_dir = os.path.join(project_root, "storage"); base_dir = os.path.join(storage_dir, "profiles")
        self.profiles = [];
        if not os.path.isdir(base_dir):
            logger.error(f"Profile directory not found: {base_dir}")
            if not os.path.isdir(storage_dir):
                 try: os.makedirs(storage_dir)
                 except OSError: pass
            if not os.path.isdir(base_dir):
                 try: os.makedirs(base_dir)
                 except OSError: logger.error(f"Failed to create profile directory: {base_dir}"); return
            return
        files = [f for f in os.listdir(base_dir) if f.endswith(".json")]; loaded_profiles = []
        for filename in sorted(files):
            try:
                with open(os.path.join(base_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("type") == "profile" and "name" in data: loaded_profiles.append((filename, data.get("name", filename)))
                    else: logger.warning(f"Skipping invalid profile file {filename}")
            except Exception as e: logger.error(f"Failed to load profile {filename}: {e}")
        self.profiles = loaded_profiles; logger.info(f"Loaded {len(self.profiles)} profiles.")

    def _show_confirmation(self, filename, name):
        confirm_screen = self.ui.screens.get("confirm")
        if not confirm_screen: return

        # --- Callbacks Modified ---
        def yes_action():
            # This code runs AFTER the confirm screen context has been popped
            logger.info(f"Profile '{name}' ({filename}) confirmed.")
            config.last_selected_profile = filename
            if hasattr(config, '__setattr__'): pass
            elif settings_manager:
                 try: settings_manager.set_setting("last_selected_profile", filename)
                 except Exception as e: logger.error(f"Failed to save setting: {e}")

            # Pop the underlying ScrollableList context
            # Check if the list component is *still* the active context before popping
            # This is less likely now, but safer.
            if self.ui.active_input_context and self.ui.active_input_context.get('component') == self.list_component:
                logger.debug("YES action popping list context.")
                self.ui.pop_context() # Pop ScrollableList
            else:
                 logger.warning("YES action: List context was not active when expected.")

            # Switch screen only AFTER all contexts are popped
            self.ui.switch_to_screen("overview")

        def no_action():
            # This code runs AFTER the confirm screen context has been popped
            logger.debug("Profile selection cancelled (NO action).")
            # Do nothing else - MenuUI redraws the underlying list automatically after pop
        # --- End Callbacks Modified ---

        confirm_screen.set_context(
            message=f"Set '{name}' as current?", on_yes=yes_action, on_no=no_action
        )
        self.ui.push_context(
            mode="confirm", component=confirm_screen, caller_screen_name="profile_selector"
        )

    # ... (draw, handle_event, update, on_exit remain the same as previous correct version with standardized tab bar) ...
    def draw(self, mode="tab_bar"):
        if not self.display: return
        lines = []
        if mode == "tab_bar":
            lines.append(f"── State: {self.ui.kiln_data.get('state', 'IDLE').upper()} ──"); lines.append("")
            allowed_tabs = self.ui.get_allowed_tabs(); current_tab_key = self.ui.current_screen_name
            our_name = "profile_selector"
            tab_display_names = { "overview": "Overview", "diagram": "Diagram", "profile_selector": "Profiles", "manual_control": "Manual", "profile_builder": "Builder", "settings": "Settings" }
            submenu_tabs = {"profile_selector", "manual_control", "profile_builder", "settings"}
            max_tabs_to_show = 6; tabs_to_display = allowed_tabs[:max_tabs_to_show]
            for tab_key in tabs_to_display:
                display_name = tab_display_names.get(tab_key, tab_key.capitalize())
                prefix = "▶" if tab_key == current_tab_key else " "; suffix = " ▶" if tab_key in submenu_tabs else ""
                lines.append(f"{prefix} [{display_name}{suffix}]")
        else: lines.append("Profile Selector"); lines.append(""); lines.append("(Loading...)")
        while len(lines) < self.display.rows: lines.append("")
        self.display.draw_lines(lines, clear_first=True)
    def handle_event(self, event):
        logger.debug(f"[ProfileSelectorScreen] handle_event({event}) called unexpectedly at level {self.ui.current_screen_level}")
        if event == "short_press" or event == "long_press": self.ui.pop_context_or_level()
    def update(self, data):
        if self.ui.current_screen_name == "profile_selector" and self.ui.current_screen_level == 0:
             if self.last_kiln_data.get('state') != data.get('state'): self.ui.redraw_current_view(); self.last_kiln_data = data.copy()
    def on_exit(self): self.list_component = None; logger.debug("[ProfileSelectorScreen] Exited.")

# --- END OF FILE: display_ui/screens/profile_selector_screen.py ---