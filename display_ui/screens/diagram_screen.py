# --- START OF FILE: display_ui/screens/diagram_screen.py ---
import logging
import json
import os
# import math # Not currently needed
from display_ui.screens.screen_base import UIScreen
import config # Assuming config is accessible for temp units

logger = logging.getLogger(__name__)

# --- Constants for Drawing ---
MARGIN_TOP = 12     # Pixels from top edge for title
MARGIN_BOTTOM = 10    # Pixels from bottom edge (can be smaller without hints)
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
    Click activates point selection mode to cycle through points using rotation.
    Left scroll (in normal mode) returns to Overview.
    """
    def __init__(self, ui):
        """Initializes the DiagramScreen state."""
        super().__init__(ui)
        self._reset_state() # Initialize all state variables

    def _reset_state(self):
        """Resets all screen-specific state variables."""
        self.profile = None; self.profile_error = None; self.scaled_points = []
        self.current_runtime = 0; self.current_temp = 0.0; self.is_running_or_paused = False
        self.selected_point_index = -1; self.point_selection_active = False
        self.last_live_data = None
        self.plot_x0 = MARGIN_LEFT; self.plot_y0 = MARGIN_TOP
        self.plot_w = 0; self.plot_h = 0; self.plot_x1 = 0; self.plot_y1 = 0
        self.time_scale = 1.0; self.temp_scale = 1.0; self.min_time = 0; self.min_temp = 0

    def _update_plot_dimensions(self):
        """Calculates plot area based on current display size."""
        if not self.display: return
        self.plot_w = self.display.width - MARGIN_LEFT - MARGIN_RIGHT
        self.plot_h = self.display.height - MARGIN_TOP - MARGIN_BOTTOM
        self.plot_x1 = self.plot_x0 + self.plot_w
        self.plot_y1 = self.display.height - MARGIN_BOTTOM # Bottom edge of plot

    def _scale_x(self, time_sec):
        """Scales time (seconds) to X pixel coordinate."""
        if self.time_scale <= 0: return self.plot_x0
        x = int(self.plot_x0 + (time_sec - self.min_time) * self.time_scale)
        return max(self.plot_x0, min(x, self.plot_x1)) # Clamp

    def _scale_y(self, temp_c):
        """Scales temperature (Celsius) to Y pixel coordinate (inverted)."""
        if self.temp_scale <= 0: return self.plot_y1
        y = int(self.plot_y1 - (temp_c - self.min_temp) * self.temp_scale)
        return max(self.plot_y0, min(y, self.plot_y1)) # Clamp

    def load_profile_data(self):
        """Loads the profile and calculates scaling factors and points."""
        self.profile = None; self.profile_error = None; self.scaled_points = [] # Reset profile parts
        self._update_plot_dimensions()
        selected_profile_filename = getattr(config, 'last_selected_profile', None)
        if not selected_profile_filename: self.profile_error = "No profile selected"; return
        try:
            script_dir = os.path.dirname(__file__)
            project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
            profile_path = os.path.join(project_root, "storage", "profiles", selected_profile_filename)
            if not os.path.exists(profile_path): self.profile_error = f"File NF:\n {selected_profile_filename[:20]}..."; return
            with open(profile_path, 'r', encoding='utf-8') as f: loaded_data = json.load(f)
            profile_data_list = loaded_data.get('data')
            if not (loaded_data.get('type') == 'profile' and isinstance(profile_data_list, list) and len(profile_data_list) >= 2):
                self.profile_error = f"Invalid format:\n {selected_profile_filename[:20]}..."; return
            self.profile = loaded_data; logger.info(f"Loaded profile: {self.profile.get('name', 'Unnamed')}")
            times = [pt[0] for pt in profile_data_list]; temps = [pt[1] for pt in profile_data_list]
            self.min_time, max_time = min(times), max(times); self.min_temp, max_temp = min(temps), max(temps)
            time_range = max_time - self.min_time; temp_range = max_temp - self.min_temp
            self.time_scale = (self.plot_w / time_range) if time_range > 0 else 1.0
            self.temp_scale = (self.plot_h / temp_range) if temp_range > 0 else 1.0
            self.scaled_points = [(self._scale_x(t), self._scale_y(temp)) for t, temp in profile_data_list]
            logger.info(f"Calculated {len(self.scaled_points)} points, scale T:{self.time_scale:.2f} S:{self.temp_scale:.2f}")
        except Exception as e:
            self.profile_error = f"Error loading:\n {selected_profile_filename[:20]}..."; logger.error(f"Failed to load/process profile {selected_profile_filename}: {e}", exc_info=True)
            self.profile = None; self.scaled_points = []

    def on_enter(self):
        """Called when switching TO this screen."""
        logger.debug(f"[DiagramScreen] on_enter (Level: {self.ui.current_screen_level})")
        if self.ui.current_screen_level == 1:
             self.load_profile_data()
             self.point_selection_active = False # Start in normal mode
             self.selected_point_index = -1
             self.last_live_data = None
        # Redraw handled by MenuUI

    def update(self, kiln_data):
        """Receives kiln_data, updates crosshair, triggers redraw if needed."""
        if not (self.ui.current_screen == self and self.ui.current_screen_level == 1 and not self.ui.active_input_context):
            if self.is_running_or_paused: self.is_running_or_paused = False; self.last_live_data = None
            return

        new_runtime = kiln_data.get("runtime", 0); new_temp = kiln_data.get("temperature", 0.0)
        new_state = kiln_data.get("state", "IDLE").upper(); new_is_running = new_state in ["RUNNING", "PAUSED"]
        new_live_data = (new_runtime, round(new_temp, 1), new_is_running)

        if new_live_data != self.last_live_data:
            # Use INFO level for critical state changes if DEBUG is off
            logger.log(logging.DEBUG if logger.isEnabledFor(logging.DEBUG) else logging.INFO,
                       f"Live data changed: RT={new_runtime}, T={new_temp:.1f}, Running={new_is_running}")
            self.current_runtime = new_runtime; self.current_temp = new_temp
            self.is_running_or_paused = new_is_running; self.last_live_data = new_live_data
            self.ui.redraw_current_view()

    def _format_time(self, seconds):
        secs = int(seconds); mins, secs = divmod(secs, 60); hrs, mins = divmod(mins, 60)
        return f"{hrs}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

    def _format_temp(self, temp_c):
        temp = float(temp_c); unit = config.temp_scale.upper()
        if unit == "F": temp = (temp * 9/5) + 32
        return f"{temp:.1f}°{unit}"

    def draw(self, mode="submenu"):
        """Draws the diagram screen content."""
        if not self.display: return
        if mode == "tab_bar": return

        logger.debug(f"Drawing submenu. PointSel Active: {self.point_selection_active}, Idx: {self.selected_point_index}")
        self.display.clear()

        # --- Error / No Data Handling ---
        if self.profile_error:
            lines = ["Diagram Error", "", *self.profile_error.split('\n')]
            while len(lines) < self.display.rows : lines.append("")
            self.display.draw_lines(lines, clear_first=False); return
        if not self.profile or not self.scaled_points:
            lines = ["Diagram", "", "No profile data loaded.", ""]
            while len(lines) < self.display.rows : lines.append("")
            self.display.draw_lines(lines, clear_first=False); return

        # --- Draw using draw_custom ---
        profile_name = self.profile.get("name", "Unnamed Profile")
        font = self.display.font_small

        def draw_content_on_buffer(draw):
            # 1. Title
            draw.text((MARGIN_LEFT, 1), profile_name[:20], font=font, fill="white")
            # 2. Profile Line
            if len(self.scaled_points) >= 2: draw.line(self.scaled_points, fill=POINT_COLOR, width=1)
            # 3. Kink Circles
            for i, (x, y) in enumerate(self.scaled_points):
                is_selected = (i == self.selected_point_index)
                radius = SELECTED_POINT_RADIUS if is_selected else POINT_RADIUS
                color = SELECTED_POINT_COLOR if is_selected else POINT_COLOR
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, fill=None)
            # 4. Crosshair
            if self.is_running_or_paused:
                cx = self._scale_x(self.current_runtime); cy = self._scale_y(self.current_temp)
                draw.line([(cx, self.plot_y0), (cx, self.plot_y1)], fill=CROSSHAIR_COLOR)
                draw.line([(self.plot_x0, cy), (self.plot_x1, cy)], fill=CROSSHAIR_COLOR)

            # 5. Selected Point Info
            info_y = self.plot_y1 + 2
            draw.rectangle((0, info_y, self.display.width, self.display.height), fill=self.display.bg_color) # Clear bottom area
            if self.point_selection_active and self.selected_point_index != -1:
                if self.selected_point_index < len(self.profile['data']):
                    time_val, temp_val = self.profile['data'][self.selected_point_index]
                    info_text = f"Pt{self.selected_point_index}: {self._format_time(time_val)}@{self._format_temp(temp_val)}"
                    text_width = draw.textlength(info_text, font=font)
                    info_x = max(MARGIN_LEFT, (self.display.width - text_width) // 2)
                    draw.text((info_x, info_y), info_text, font=font, fill=SELECTED_POINT_COLOR)

            # --- REMOVED Navigation Hints ---

        # Execute drawing
        self.display.draw_custom(draw_content_on_buffer, clear_first=False)

    def enter_screen(self):
        """Called on short press from Tab Bar."""
        logger.info("[DiagramScreen] enter_screen -> entering submenu") # Use INFO for visibility
        self.load_profile_data()
        self.selected_point_index = -1
        self.point_selection_active = False
        self.last_live_data = None
        return "enter_submenu"

    def handle_event(self, event):
        """Handles events when DiagramScreen is active (Level 1)."""
        # Use INFO for entry point to ensure visibility
        logger.info(f"[DiagramScreen] handle_event '{event}' ModeActive: {self.point_selection_active}")
        if self.ui.current_screen_level != 1: return # Safety check

        needs_redraw = False
        num_points = len(self.scaled_points)

        # --- Point Selection Mode Active ---
        if self.point_selection_active:
            if event == "rot_left":
                if num_points > 0:
                    self.selected_point_index -= 1
                    if self.selected_point_index < -1: self.selected_point_index = num_points - 1
                    logger.info(f"Point Sel Mode: Left -> Index {self.selected_point_index}")
                    needs_redraw = True
            elif event == "rot_right":
                if num_points > 0:
                    self.selected_point_index += 1
                    if self.selected_point_index >= num_points: self.selected_point_index = -1
                    logger.info(f"Point Sel Mode: Right -> Index {self.selected_point_index}")
                    needs_redraw = True
            elif event == "short_press":
                logger.info("Point Sel Mode: Click -> Exiting Mode")
                self.point_selection_active = False
                self.selected_point_index = -1 # Deselect point
                needs_redraw = True
            # Long press handled globally

        # --- Normal View Mode ---
        else: # point_selection_active is False
            if event == "rot_left":
                # --- This block should be reached ---
                logger.info("Normal Mode: Left -> Requesting switch to Overview")
                return ("switch_and_enter", "overview") # Request switch
                # --- End block ---
            elif event == "rot_right":
                logger.info("Normal Mode: Right -> No Action")
                pass
            elif event == "short_press":
                if num_points > 0:
                    logger.info("Normal Mode: Click -> Entering Point Select Mode")
                    self.point_selection_active = True
                    self.selected_point_index = 0 # Start at first point
                    needs_redraw = True
                else:
                    logger.info("Normal Mode: Click -> No points to select.")
            # Long press handled globally

        # Trigger redraw if state changed within this handler
        if needs_redraw:
            self.ui.redraw_current_view()

        return None # Indicate event was processed here if not returning tuple

    def on_exit(self):
        """Called by MenuUI just before switching away."""
        logger.debug("[DiagramScreen] on_exit")
        self._reset_state() # Reset state when leaving

# --- END OF FILE: display_ui/screens/diagram_screen.py ---