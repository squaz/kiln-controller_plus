# --- START OF FILE: display_ui/screens/overview_screen.py ---
import logging
import time
import config # Needed for profile fallback
from display_ui.screens.screen_base import UIScreen

logger = logging.getLogger(__name__)

class OverviewScreen(UIScreen):
    """
    Displays detailed kiln status information on a dedicated page (submenu).
    Handles Pause/Stop/Start confirmation actions via short press within the submenu.
    Handles navigation back to tab bar (left) or directly to Diagram screen (right).
    """
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self.last_displayed_data = {}
        self.local_ip_text = "IP: Missing" # Placeholder

    def on_enter(self):
        logger.debug(f"[OverviewScreen] on_enter (Level: {self.ui.current_screen_level})")
        if self.ui.current_screen_level == 1:
            self.last_displayed_data = {} # Reset comparison data for submenu view

    def enter_screen(self):
        """Handles short press from Tab Bar (Level 0) -> Enters submenu."""
        logger.debug("[OverviewScreen] enter_screen -> entering submenu")
        self.last_displayed_data = {}
        return "enter_submenu" # Tell MenuUI to go to Level 1

    def _format_data(self, data):
        """Helper function to format raw kiln data for display."""
        # ... (Keep the same formatting logic) ...
        if data is None: data = {}
        temp = data.get("temperature", 0.0); target = data.get("target", 0.0)
        state = data.get("state", "IDLE").upper()
        profile_name = data.get("profile") or getattr(config, 'last_selected_profile', None) or "N/A"
        if isinstance(profile_name, str) and profile_name.endswith(".json"): profile_name = profile_name[:-5]
        runtime_sec = int(data.get("runtime", 0)); hours, rem = divmod(runtime_sec, 3600); mins, secs = divmod(rem, 60)
        runtime_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
        action_label = "";
        if state == "RUNNING": action_label = "[ Click to Pause ]"
        elif state == "PAUSED": action_label = "[ Click to Stop ]"
        elif state == "IDLE": action_label = "[ Click to Start ]"
        return {"state": state, "temp": temp, "target": target, "profile_name": profile_name, "runtime_str": runtime_str, "action_label": action_label}


    def handle_event(self, event):
        """Handles events when in the submenu (Level 1)."""
        logger.debug(f"[OverviewScreen] handle_event '{event}' at Level {self.ui.current_screen_level}")
        if self.ui.current_screen_level != 1: return # Safety check

        if event == "rot_left":
            logger.debug("Rotary Left -> Returning to Tab Bar")
            self.ui.pop_context_or_level() # Go back to Level 0
            return None # Indicate event handled
        elif event == "rot_right":
            logger.debug("Rotary Right -> Requesting switch and enter Diagram")
            # Return special tuple for MenuUI to handle
            return ("switch_and_enter", "diagram")
        elif event == "short_press":
            logger.debug("Short Press in submenu -> Triggering confirmation")
            action_pushed = self._trigger_confirmation()
            # Return a value indicating if a context was pushed
            return "context_pushed" if action_pushed else None

        return None # No specific action taken by this handler for other events

    def _trigger_confirmation(self):
        """Pushes the confirmation screen based on current kiln state."""
        state = self.ui.kiln_data.get("state", "IDLE").upper()
        confirm_screen = self.ui.screens.get("confirm")
        if not confirm_screen: logger.error("[OverviewScreen] ConfirmScreen not found!"); return False

        action_pushed = False

        # --- Define actions (callbacks passed to ConfirmScreen) ---
        # Note: These callbacks run AFTER ConfirmScreen pops itself.
        def no_action():
            logger.debug("Confirmation cancelled (NO action executed).")
            # Nothing more needed here, context was popped by ConfirmScreen

        if state == "RUNNING":
            def yes_action_pause():
                logger.info("✅ Pause confirmed by user. (Action TBD)")
                # --- TODO: Add actual pause command call ---
            confirm_screen.set_context("Pause the kiln?", yes_action_pause, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        elif state == "PAUSED":
            def yes_action_stop():
                logger.info("🛑 Stop confirmed by user. (Action TBD)")
                # --- TODO: Add actual stop command call ---
            confirm_screen.set_context("Stop the kiln?", yes_action_stop, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        elif state == "IDLE":
            def yes_action_start():
                logger.info("▶️ Start confirmed by user. (Action TBD)")
                profile_to_start = getattr(config, 'last_selected_profile', None)
                if profile_to_start:
                    logger.info(f"   Attempting to start profile: {profile_to_start}")
                    # --- TODO: Add actual start profile command call ---
                else:
                    logger.warning("   No profile selected to start!")
            selected_profile_name = getattr(config, 'last_selected_profile', 'N/A')
            if isinstance(selected_profile_name, str) and selected_profile_name.endswith(".json"): selected_profile_name = selected_profile_name[:-5]
            confirm_screen.set_context(f"Start '{selected_profile_name[:10]}'?", yes_action_start, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        else:
            logger.debug(f"Short press in Overview submenu ignored (state is {state}).")

        return action_pushed


    def update(self, kiln_data):
        """Receives kiln_data. Redraws submenu if visible data changed."""
        if not (self.ui.current_screen == self and self.ui.current_screen_level == 1 and not self.ui.active_input_context):
            return # Only update if visible in submenu mode

        new_formatted = self._format_data(kiln_data)
        last_formatted = self._format_data(self.last_displayed_data)
        needs_redraw = False
        fields_to_check = ["state", "temp", "target", "profile_name", "runtime_str", "action_label"]
        for field in fields_to_check:
            if field in ["temp", "target"]:
                 if abs(new_formatted.get(field, 0.0) - last_formatted.get(field, -1.0)) > 0.1: needs_redraw = True; break
            elif new_formatted.get(field) != last_formatted.get(field): needs_redraw = True; break

        if needs_redraw:
            logger.debug("[OverviewScreen] Data changed, triggering submenu redraw.")
            self.last_displayed_data = kiln_data.copy() # Update BEFORE redraw
            self.ui.redraw_current_view() # Triggers self.draw(mode="submenu")

    def draw(self, mode="submenu"):
        """Draws the detailed overview submenu OR handles tab bar mode."""
        if not self.display: return

        if mode == "tab_bar":
            # Handled by TabBar component via MenuUI
            return
        else:
            # --- Draw the Detailed Submenu View (Level 1) ---
            logger.info("[OverviewScreen] Drawing full screen submenu view.")
            data = self.ui.kiln_data or {}
            formatted = self._format_data(data)
            ip_line = self.local_ip_text # Use placeholder

            lines = [
                f" State: {formatted['state']}", # No title line
                f" Temp:  {formatted['temp']:>6.1f}{config.temp_scale.upper()}",
                f" Target:{formatted['target']:>6.1f}{config.temp_scale.upper()}",
                f" Runtime: {formatted['runtime_str']}",
                f" Profile: {formatted['profile_name'][:11]}",
                "",
                f" {ip_line}",
                "",
                f"{formatted['action_label']}", # Action hint
            ]
            # Pad remaining lines
            while len(lines) < self.display.rows: lines.append("")
            # Draw all lines, clearing buffer first
            self.display.draw_lines(lines[:self.display.rows], clear_first=True)
            # --- End Detailed Submenu View ---

    def on_exit(self):
        logger.debug("[OverviewScreen] on_exit")
        self.last_displayed_data = {}

# --- END OF FILE: display_ui/screens/overview_screen.py ---