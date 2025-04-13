# --- START OF FILE: display_ui/screens/diagram_screen.py ---
import logging
import json
import os
import math # Used for ceiling/floor if needed
from display_ui.screens.screen_base import UIScreen
import config # Assuming config is accessible for temp units

logger = logging.getLogger(__name__)

# --- Constants for Drawing ---
MARGIN_TOP = 12     # Pixels from top edge for title
MARGIN_BOTTOM = 18    # Pixels from bottom edge (increased for info text)
MARGIN_LEFT = 4       # Pixels from left edge
MARGIN_RIGHT = 4      # Pixels from right edge
POINT_RADIUS = 2      # Radius of normal profile point circles
SELECTED_POINT_RADIUS = 3 # Radius of the highlighted point circle
CROSSHAIR_COLOR = "dimgray" # Color for the live crosshair
POINT_COLOR = "white"
SELECTED_POINT_COLOR = "yellow"

class DiagramScreen(UIScreen):
    """
    Displays an interactive graph of the selected firing profile.
    Shows current progress via a crosshair when running.
    Allows cycling through profile points (kinks) using right scroll
    to view details. Left scroll returns to Overview.
    """
    def __init__(self, ui):
        """Initializes the DiagramScreen state."""
        super().__init__(ui)
        # --- State Variables ---
        self.profile = None           # Currently loaded profile dict {name:..., data:[[t,T],...]}
        self.profile_error = None     # Error message if loading failed
        self.scaled_points = []       # List of (x_px, y_px) pixel coords for profile points
        self.current_runtime = 0      # Latest runtime from kiln data
        self.current_temp = 0.0       # Latest temperature from kiln data
        self.is_running_or_paused = False # Track if kiln active for crosshair display
        self.selected_point_index = -1 # Index of highlighted profile point (-1 for none)
        self.last_live_data = None    # Store last runtime/temp/state for update comparison

        # --- Plotting Area (calculated dynamically) ---
        self.plot_x0 = MARGIN_LEFT
        self.plot_y0 = MARGIN_TOP
        self.plot_w = 0
        self.plot_h = 0
        self.plot_x1 = 0 # plot_x0 + plot_w
        self.plot_y1 = 0 # display.height - MARGIN_BOTTOM

        # --- Scaling Factors (calculated dynamically) ---
        self.time_scale = 1.0 # pixels per second
        self.temp_scale = 1.0 # pixels per degree
        self.min_time = 0
        self.min_temp = 0
        # --- End State Variables ---

    def _reset_state(self):
        """Resets screen-specific state."""
        self.profile = None
        self.profile_error = None
        self.scaled_points = []
        self.selected_point_index = -1
        self.current_runtime = 0
        self.current_temp = 0.0
        self.is_running_or_paused = False
        self.last_live_data = None
        self.time_scale = 1.0
        self.temp_scale = 1.0
        self.min_time = 0
        self.min_temp = 0

    def _update_plot_dimensions(self):
        """Calculates plot area based on current display size."""
        if not self.display: return
        self.plot_w = self.display.width - MARGIN_LEFT - MARGIN_RIGHT
        self.plot_h = self.display.height - MARGIN_TOP - MARGIN_BOTTOM
        self.plot_x1 = self.plot_x0 + self.plot_w
        # Y-axis inverted for drawing (0 at top)
        self.plot_y1 = self.display.height - MARGIN_BOTTOM

    def _scale_x(self, time_sec):
        """Scales time (seconds) to X pixel coordinate within plot bounds."""
        if self.time_scale <= 0: return self.plot_x0 # Avoid division by zero
        # Clamp result within plot area horizontally
        x = int(self.plot_x0 + (time_sec - self.min_time) * self.time_scale)
        return max(self.plot_x0, min(x, self.plot_x1))

    def _scale_y(self, temp_c):
        """Scales temperature (Celsius) to Y pixel coordinate (inverted)."""
        if self.temp_scale <= 0: return self.plot_y1 # Avoid division by zero
        # Y=0 is at the top, so subtract from bottom edge of plot area
        y = int(self.plot_y1 - (temp_c - self.min_temp) * self.temp_scale)
        # Clamp result within plot area vertically
        return max(self.plot_y0, min(y, self.plot_y1))

    def load_profile_data(self):
        """Loads the profile and calculates scaling factors and points."""
        self._reset_state()
        self._update_plot_dimensions() # Update plot geometry first
        selected_profile_filename = getattr(config, 'last_selected_profile', None)

        if not selected_profile_filename:
            self.profile_error = "No profile selected"; return

        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
            profile_path = os.path.join(project_root, "storage", "profiles", selected_profile_filename)

            if not os.path.exists(profile_path):
                self.profile_error = f"File not found:\n {selected_profile_filename[:20]}..."; return

            with open(profile_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            # Basic Validation
            profile_data_list = loaded_data.get('data')
            if not (loaded_data.get('type') == 'profile' and
                    isinstance(profile_data_list, list) and
                    len(profile_data_list) >= 2):
                self.profile_error = f"Invalid format:\n {selected_profile_filename[:20]}..."; return

            self.profile = loaded_data
            logger.info(f"[DiagramScreen] Loaded profile: {self.profile.get('name', 'Unnamed')}")

            # --- Calculate Scaling ---
            times = [pt[0] for pt in profile_data_list]; temps = [pt[1] for pt in profile_data_list]
            self.min_time, max_time = min(times), max(times)
            self.min_temp, max_temp = min(temps), max(temps)

            time_range = max_time - self.min_time
            temp_range = max_temp - self.min_temp

            # Prevent division by zero and scale to fit plot area
            self.time_scale = (self.plot_w / time_range) if time_range > 0 else 1.0
            self.temp_scale = (self.plot_h / temp_range) if temp_range > 0 else 1.0

            # --- Calculate Scaled Points ---
            self.scaled_points = [(self._scale_x(t), self._scale_y(temp)) for t, temp in profile_data_list]
            logger.debug(f"Calculated {len(self.scaled_points)} scaled points.")

        except Exception as e:
            self.profile_error = f"Error loading:\n {selected_profile_filename[:20]}..."
            logger.error(f"Failed to load/process profile {selected_profile_filename}: {e}", exc_info=True)
            self._reset_state() # Ensure state is clean on error

    def on_enter(self):
        """Called when switching TO this screen."""
        logger.debug(f"[DiagramScreen] on_enter (Level: {self.ui.current_screen_level})")
        # Load/Reload data only when entering the submenu state
        if self.ui.current_screen_level == 1:
             self.load_profile_data()
             self.selected_point_index = -1 # Reset selection
             self.last_live_data = None    # Reset comparison data
        # Redraw handled by MenuUI

    def update(self, kiln_data):
        """Receives kiln_data, stores live data, triggers redraw if needed."""
        # Only update if Diagram is the active view (Level 1) and no component active
        if not (self.ui.current_screen == self and self.ui.current_screen_level == 1 and not self.ui.active_input_context):
            # Clear live data if screen not active to remove crosshair on next draw if needed
            if self.is_running_or_paused:
                 self.is_running_or_paused = False
                 self.last_live_data = None # Ensure redraw if we become active again
            return

        new_runtime = kiln_data.get("runtime", 0)
        new_temp = kiln_data.get("temperature", 0.0)
        new_state = kiln_data.get("state", "IDLE").upper()
        new_is_running = new_state in ["RUNNING", "PAUSED"]

        # Compare relevant live data points
        new_live_data = (new_runtime, round(new_temp, 1), new_is_running)

        if new_live_data != self.last_live_data:
            logger.debug(f"Live data changed: {new_live_data} (was {self.last_live_data})")
            self.current_runtime = new_runtime
            self.current_temp = new_temp
            self.is_running_or_paused = new_is_running
            self.last_live_data = new_live_data # Store new data for comparison
            self.ui.redraw_current_view() # Trigger redraw

    def _format_time(self, seconds):
        """Helper to format seconds into MM:SS or H:MM:SS"""
        secs = int(seconds)
        mins, secs = divmod(secs, 60)
        hrs, mins = divmod(mins, 60)
        return f"{hrs}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

    def _format_temp(self, temp_c):
        """Helper to format temperature based on config scale"""
        temp = float(temp_c)
        unit = config.temp_scale.upper()
        if unit == "F": temp = (temp * 9/5) + 32
        # Use 1 decimal place for point info for precision
        return f"{temp:.1f}°{unit}"

    def draw(self, mode="submenu"):
        """Draws the diagram screen content."""
        if not self.display: return
        if mode == "tab_bar": return # Handled by TabBar component

        logger.debug(f"[DiagramScreen] Drawing submenu. Selected point: {self.selected_point_index}")
        self.display.clear() # Clear buffer for this screen

        # --- Error / No Data Handling ---
        if self.profile_error:
            lines = ["Diagram Error", "", *self.profile_error.split('\n')]
            while len(lines) < self.display.rows -1 : lines.append("") # Leave room for nav hint
            lines.append("Hold: Back | < Overview")
            self.display.draw_lines(lines, clear_first=False); return
        if not self.profile or not self.scaled_points:
            lines = ["Diagram", "", "No profile data loaded.", ""]
            while len(lines) < self.display.rows -1 : lines.append("")
            lines.append("Hold: Back | < Overview")
            self.display.draw_lines(lines, clear_first=False); return

        # --- Draw using draw_custom ---
        profile_name = self.profile.get("name", "Unnamed Profile")
        font = self.display.font_small

        def draw_content_on_buffer(draw):
            # 1. Draw Title
            draw.text((MARGIN_LEFT, 1), profile_name[:20], font=font, fill="white")

            # 2. Draw Profile Line
            if len(self.scaled_points) >= 2:
                draw.line(self.scaled_points, fill=POINT_COLOR, width=1)

            # 3. Draw Kink Circles
            for i, (x, y) in enumerate(self.scaled_points):
                is_selected = (i == self.selected_point_index)
                radius = SELECTED_POINT_RADIUS if is_selected else POINT_RADIUS
                color = SELECTED_POINT_COLOR if is_selected else POINT_COLOR
                # Draw outline circle
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, fill=None)

            # 4. Draw Crosshair (if active)
            if self.is_running_or_paused:
                cx = self._scale_x(self.current_runtime)
                cy = self._scale_y(self.current_temp)
                # Draw thin crosshair lines within plot bounds
                draw.line([(cx, self.plot_y0), (cx, self.plot_y1)], fill=CROSSHAIR_COLOR) # Vertical
                draw.line([(self.plot_x0, cy), (self.plot_x1, cy)], fill=CROSSHAIR_COLOR) # Horizontal

            # 5. Draw Selected Kink Info OR Navigation Hints
            info_y = self.plot_y1 + 2 # Position below the graph area
            # Clear the bottom area for text
            draw.rectangle((0, info_y, self.display.width, self.display.height), fill=self.display.bg_color)

            if self.selected_point_index != -1 and self.selected_point_index < len(self.profile['data']):
                # Display selected point details
                time_val, temp_val = self.profile['data'][self.selected_point_index]
                info_text = f"Pt{self.selected_point_index}: {self._format_time(time_val)} @ {self._format_temp(temp_val)}"
                text_width = draw.textlength(info_text, font=font)
                info_x = max(MARGIN_LEFT, (self.display.width - text_width) // 2) # Center
                draw.text((info_x, info_y), info_text, font=font, fill=SELECTED_POINT_COLOR)
            else:
                # Display general navigation hints
                hint_text = "< Overview | Cycle Pts > | Hold: Back"
                text_width = draw.textlength(hint_text, font=font)
                hint_x = max(MARGIN_LEFT, (self.display.width - text_width) // 2) # Center
                draw.text((hint_x, info_y), hint_text, font=font, fill=POINT_COLOR)

        # Execute the drawing function on the buffer (it was already cleared)
        self.display.draw_custom(draw_content_on_buffer, clear_first=False)

    def enter_screen(self):
        """Called on short press from Tab Bar. Enters the diagram view."""
        logger.debug("[DiagramScreen] enter_screen -> entering submenu")
        self.load_profile_data() # Load data and calculate points
        self.selected_point_index = -1 # Ensure no point selected on entry
        self.last_live_data = None
        return "enter_submenu" # Tell MenuUI level changed

    def handle_event(self, event):
        """Handles events when DiagramScreen is active (Level 1)."""
        logger.debug(f"[DiagramScreen] handle_event '{event}' at Level {self.ui.current_screen_level}")
        if self.ui.current_screen_level != 1: return # Safety check

        needs_redraw = False
        if event == "rot_left":
            logger.debug("Rotary Left -> Requesting switch and enter Overview")
            return ("switch_and_enter", "overview") # Request switch

        elif event == "rot_right":
            # Cycle through kinks, including -1 for 'none selected'
            num_points = len(self.scaled_points)
            if num_points > 0:
                self.selected_point_index += 1
                # Wrap around logic: -1, 0, 1, ..., n-1, -1
                if self.selected_point_index >= num_points:
                    self.selected_point_index = -1
                logger.debug(f"Rotary Right -> Selected kink index: {self.selected_point_index}")
                needs_redraw = True # Need redraw to show new selection/text
            else:
                logger.debug("Rotary Right -> No points to select.")
            # Trigger redraw immediately if selection changed
            if needs_redraw: self.ui.redraw_current_view()
            return None # Event handled

        # Long press handled globally
        # Short press currently does nothing
        return None # Indicate event not handled by specific actions above

    def on_exit(self):
        """Called by MenuUI just before switching away."""
        logger.debug("[DiagramScreen] on_exit")
        self._reset_state() # Reset state when leaving

# --- END OF FILE: display_ui/screens/diagram_screen.py ---