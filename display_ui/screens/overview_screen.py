# --- START OF FILE: display_ui/screens/overview_screen.py ---
import logging
import time
import config # Needed for profile fallback
from display_ui.screens.screen_base import UIScreen

logger = logging.getLogger(__name__)

class OverviewScreen(UIScreen):
    """
    Displays the main kiln overview information as a full screen when selected
    in the tab bar (Level 0).
    Handles Pause/Stop/Start confirmation actions via short press.
    """
    def __init__(self, ui_manager):
        """Initializes the OverviewScreen."""
        super().__init__(ui_manager)
        self.last_displayed_data = {} # For update comparison
        # Placeholder for IP address - Fetching handled elsewhere or later
        self.local_ip_text = "IP: Missing"

    def on_enter(self):
        """Called when Overview becomes the current_screen (active tab)."""
        logger.debug("[OverviewScreen] on_enter (Level 0)")
        # Reset comparison data to force a full redraw next time data updates
        self.last_displayed_data = {}
        # Redraw is handled by MenuUI calling redraw_current_view,
        # which will now directly call this screen's draw() method.

    def enter_screen(self):
        """Handles short press action when Overview is the active tab (Level 0)."""
        logger.debug("[OverviewScreen] enter_screen called (short press)")
        self._trigger_confirmation()
        # Determine if a context was pushed to inform MenuUI
        state = self.ui.kiln_data.get("state", "IDLE").upper()
        if state in ["RUNNING", "PAUSED", "IDLE"]:
             return "context_pushed" # A confirm screen was likely pushed
        else:
             return None # No action taken, stay at level 0

    def _trigger_confirmation(self):
        """Pushes the confirmation screen based on current kiln state."""
        state = self.ui.kiln_data.get("state", "IDLE").upper()
        confirm_screen = self.ui.screens.get("confirm")
        if not confirm_screen: logger.error("[OverviewScreen] ConfirmScreen not found!"); return

        def no_action(): logger.debug("Confirmation cancelled (NO action).") # ConfirmScreen handles pop

        action_pushed = False
        if state == "RUNNING":
            def yes_action_pause(): logger.info("✅ Pause confirmed. (Action TBD)"); # ConfirmScreen handles pop
            confirm_screen.set_context("Pause the kiln?", yes_action_pause, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        elif state == "PAUSED":
            def yes_action_stop(): logger.info("🛑 Stop confirmed. (Action TBD)"); # ConfirmScreen handles pop
            confirm_screen.set_context("Stop the kiln?", yes_action_stop, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        elif state == "IDLE":
            def yes_action_start():
                logger.info("▶️ Start confirmed. (Action TBD)"); # ConfirmScreen handles pop
                profile_to_start = getattr(config, 'last_selected_profile', None)
                if profile_to_start: logger.info(f"   Attempting to start profile: {profile_to_start}")
                else: logger.warning("   No profile selected to start!")
            selected_profile_name = getattr(config, 'last_selected_profile', 'N/A')
            if selected_profile_name.endswith(".json"): selected_profile_name = selected_profile_name[:-5]
            confirm_screen.set_context(f"Start '{selected_profile_name[:10]}'?", yes_action_start, no_action)
            self.ui.push_context("confirm", confirm_screen, "overview"); action_pushed = True
        else: logger.debug(f"Short press in Overview ignored (state is {state}).")

        return action_pushed # Indicate if confirm screen was shown

    def _format_data(self, data):
        """Helper function to format raw kiln data for display."""
        # ... (Keep the same formatting logic as before) ...
        if data is None: data = {}
        temp = data.get("temperature", 0.0); target = data.get("target", 0.0)
        state = data.get("state", "IDLE").upper()
        profile_name = data.get("profile") or getattr(config, 'last_selected_profile', None) or "N/A"
        if isinstance(profile_name, str) and profile_name.endswith(".json"): profile_name = profile_name[:-5]
        runtime_sec = int(data.get("runtime", 0)); hours, rem = divmod(runtime_sec, 3600); mins, secs = divmod(rem, 60)
        runtime_str = f"{hours}:{mins:02d}:{secs:02d}" if hours > 0 else f"{mins:02d}:{secs:02d}"
        action_label = ""
        if state == "RUNNING": action_label = "[ Click to Pause ]"
        elif state == "PAUSED": action_label = "[ Click to Stop ]"
        elif state == "IDLE": action_label = "[ Click to Start ]"
        return {"state": state, "temp": temp, "target": target, "profile_name": profile_name, "runtime_str": runtime_str, "action_label": action_label}

    def handle_event(self, event):
        """Overview screen does not have a distinct submenu state anymore, so this is not used."""
        logger.warning(f"[OverviewScreen] handle_event '{event}' called unexpectedly.")
        pass

    def update(self, kiln_data):
        """Receives kiln_data. Triggers redraw if visible data changed."""
        # Only update if Overview is the active screen AND no modal is active
        if not (self.ui.current_screen == self and not self.ui.active_input_context):
            return

        new_formatted = self._format_data(kiln_data)
        last_formatted = self._format_data(self.last_displayed_data)
        needs_redraw = False
        fields_to_check = ["state", "temp", "target", "profile_name", "runtime_str", "action_label"]
        for field in fields_to_check:
            if field in ["temp", "target"]:
                 if abs(new_formatted.get(field, 0.0) - last_formatted.get(field, -1.0)) > 0.1: needs_redraw = True; break
            elif new_formatted.get(field) != last_formatted.get(field): needs_redraw = True; break

        if needs_redraw:
            logger.debug("[OverviewScreen] Data changed, triggering redraw.")
            # Update comparison data BEFORE triggering redraw
            self.last_displayed_data = kiln_data.copy()
            # Let MenuUI handle calling draw method
            self.ui.redraw_current_view()


    def draw(self, mode="submenu"): # Mode is less relevant now, always draws full view
        """Draws the detailed overview screen."""
        logger.info("[OverviewScreen] Drawing full screen view.") # Add log
        if not self.display: return

        # Get current data for drawing
        data = self.ui.kiln_data or {}
        formatted = self._format_data(data)
        ip_line = self.local_ip_text # Use placeholder

        lines = [
            f" State: {formatted['state']}", # No title needed, takes full screen
            f" Temp:  {formatted['temp']:>6.1f}{config.temp_scale.upper()}",
            f" Target:{formatted['target']:>6.1f}{config.temp_scale.upper()}",
            f" Runtime: {formatted['runtime_str']}",
            f" Profile: {formatted['profile_name'][:11]}", # Truncate long profile names
            "", # Blank spacer line
            f" {ip_line}",
            "", # Spacer
            f"{formatted['action_label']}", # Action hint
        ]

        # Pad remaining lines
        while len(lines) < self.display.rows:
            lines.append("")

        # Draw all lines, clearing buffer first
        self.display.draw_lines(lines[:self.display.rows], clear_first=True)
        # No need to update last_displayed_data here, update() handles it before redraw


    # draw_details method is REMOVED

    def on_exit(self):
        """Called when switching away from this screen."""
        logger.debug("[OverviewScreen] on_exit")
        self.last_displayed_data = {} # Clear data when leaving

# --- END OF FILE: display_ui/screens/overview_screen.py ---