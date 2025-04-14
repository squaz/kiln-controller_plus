# --- START OF FILE: display_ui/screens/overview_screen.py ---
import logging
import time
import config
import json # Needed for Profile loading in start action
from display_ui.screens.screen_base import UIScreen
from lib.oven import Profile # Import Profile class if needed for start

logger = logging.getLogger(__name__)

class OverviewScreen(UIScreen):
    """
    Displays detailed kiln status. Handles Start/Stop confirmation actions via
    short press within the submenu. Left=Diagram, Right=Profiles.
    """
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self.last_displayed_data = {}
        self.local_ip_text = "IP: Missing"

    def on_enter(self):
        logger.debug(f"[OverviewScreen] on_enter (Level: {self.ui.current_screen_level})")
        if self.ui.current_screen_level == 1: self.last_displayed_data = {}

    def enter_screen(self):
        logger.debug("[OverviewScreen] enter_screen -> entering submenu")
        self.last_displayed_data = {}; return "enter_submenu"

    def _format_data(self, data):
        """Helper function to format raw kiln data for display."""
        if data is None: data = {}
        temp = data.get("temperature", 0.0); target = data.get("target", 0.0)
        state = data.get("state", "IDLE").upper()
        profile_name = data.get("profile") or getattr(config, 'last_selected_profile', None) or "N/A"
        if isinstance(profile_name, str) and profile_name.endswith(".json"): profile_name = profile_name[:-5]
        runtime_sec = int(data.get("runtime", 0)); hours, rem = divmod(runtime_sec, 3600); mins, secs = divmod(rem, 60)
        runtime_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"

        # --- MODIFIED Action Label Logic ---
        action_label = ""
        if state == "RUNNING" or state == "PAUSED": # Treat RUNNING and PAUSED the same for click action
            action_label = "[ Click to Stop ]"
        elif state == "IDLE":
            action_label = "[ Click to Start ]"
        # --- END MODIFIED ---

        return {"state": state, "temp": temp, "target": target, "profile_name": profile_name, "runtime_str": runtime_str, "action_label": action_label}

    def handle_event(self, event):
        """Handles events when in the submenu (Level 1)."""
        logger.info(f"Handle Event: {event}, Lvl: {self.ui.current_screen_level}")
        if self.ui.current_screen_level != 1: return

        if event == "rot_left":
            # Go back to Level 0 (Tab Bar view)
            logger.info("Overview L1: Rotary Left -> Returning to Tab Bar")
            self.ui.pop_context_or_level() # Sets level to 0 and redraws
            return None # Indicate event handled
        elif event == "rot_right":
            # Request switch to Diagram screen, entering its submenu
            logger.info("Overview L1: Rotary Right -> Requesting switch and enter Diagram")
            # Return special tuple for MenuUI to process
            return ("switch_and_enter", "diagram")
        elif event == "short_press":
             # Trigger confirmation for Start or Stop
            action_pushed = self._trigger_confirmation()
            return "context_pushed" if action_pushed else None

        return None # No action for other events

    def _trigger_confirmation(self):
        """Pushes the confirmation screen for Start or Stop actions."""
        state = self.ui.kiln_data.get("state", "IDLE").upper()
        confirm_screen = self.ui.screens.get("confirm")
        if not confirm_screen: logger.error("ConfirmScreen not found!"); return False

        action_pushed = False
        callbacks = self.ui.action_callbacks

        def no_action(): logger.debug("Confirmation cancelled (NO action).")

        if state == "RUNNING" or state == "PAUSED": # Combine Running and Paused states
            stop_callback = callbacks.get('stop')
            def yes_action_stop():
                logger.info("🛑 Stop confirmed by user.")
                if callable(stop_callback):
                    try: stop_callback()
                    except Exception as e: logger.error(f"Error calling stop callback: {e}")
                else: logger.error("Stop action callback not configured!")
            confirm_screen.set_context("Stop the kiln run?", yes_action_stop, no_action) # Unified message
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True

        elif state == "IDLE":
            start_callback = callbacks.get('start')
            def yes_action_start():
                logger.info("▶️ Start confirmed by user.")
                profile_to_start = getattr(config, 'last_selected_profile', None)
                if profile_to_start and callable(start_callback):
                    logger.info(f"   Attempting to start profile: {profile_to_start}")
                    try: start_callback(profile_to_start)
                    except Exception as e: logger.error(f"Error calling start callback: {e}")
                elif not profile_to_start: logger.warning("   No profile selected to start!")
                else: logger.error("Start action callback not configured!")
            selected_profile_name = getattr(config, 'last_selected_profile', 'N/A')
            if isinstance(selected_profile_name, str) and selected_profile_name.endswith(".json"): selected_profile_name = selected_profile_name[:-5]
            confirm_screen.set_context(f"Start '{selected_profile_name[:10]}'?", yes_action_start, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True

        else: # Other states (e.g., ERROR) - no action on click
            logger.debug(f"Short press in Overview submenu ignored (state is {state}).")

        return action_pushed

    def update(self, kiln_data):
        """Receives kiln_data. Redraws submenu if visible data changed."""
        if not (self.ui.current_screen == self and self.ui.current_screen_level == 1 and not self.ui.active_input_context): return
        new_formatted = self._format_data(kiln_data); last_formatted = self._format_data(self.last_displayed_data)
        needs_redraw = False; fields_to_check = ["state", "temp", "target", "profile_name", "runtime_str", "action_label"]
        for field in fields_to_check:
            new_val = new_formatted.get(field); last_val = last_formatted.get(field)
            if field in ["temp", "target"]:
                 if abs(new_val - last_val) > 0.1: needs_redraw = True; break
            elif new_val != last_val: needs_redraw = True; break
        if needs_redraw:
            logger.debug("[OverviewScreen] Data changed, triggering submenu redraw.")
            self.last_displayed_data = kiln_data.copy(); self.ui.redraw_current_view()

    def draw(self, mode="submenu"):
        """Draws the detailed overview screen."""
        if not self.display: return;
        if mode == "tab_bar": return # Handled by TabBar component

        logger.info("[OverviewScreen] Drawing full screen submenu view.")
        data = self.ui.kiln_data or {}; formatted = self._format_data(data); ip_line = self.local_ip_text
        lines = [
            f" State: {formatted['state']}",
            f" Temp:  {formatted['temp']:>6.1f}{config.temp_scale.upper()}",
            f" Target:{formatted['target']:>6.1f}{config.temp_scale.upper()}",
            f" Runtime: {formatted['runtime_str']}",
            f" Profile: {formatted['profile_name'][:11]}",
            "",
            f" {ip_line}",
            "",
            f"{formatted['action_label']}", # Will now show [ Click to Stop ] when RUNNING
        ]
        while len(lines) < self.display.rows: lines.append("")
        self.display.draw_lines(lines[:self.display.rows], clear_first=True)

    def on_exit(self):
        logger.debug("[OverviewScreen] on_exit"); self.last_displayed_data = {}

# --- END OF FILE: display_ui/screens/overview_screen.py ---