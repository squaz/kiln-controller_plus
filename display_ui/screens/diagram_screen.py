# display_ui/screens/diagram_screen.py
import logging
from display_ui.screens.screen_base import UIScreen
import config

logger = logging.getLogger(__name__)

class DiagramScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.profile = None # Loaded dynamically

    def load_profile_data(self):
        """Loads the currently selected profile data."""
        # TODO: Implement proper loading based on config.last_selected_profile
        # For now, using placeholder data
        self.profile = {
            "type": "profile",
            "name": config.last_selected_profile or "No Profile",
            "data": [ # Default/placeholder data
                [0, 20], [3600, 600], [7200, 900], [10800, 1080], [14400, 1080]
                # Add more realistic points later
            ]
        }
        # Actual implementation should load from JSON file specified in config
        # profile_path = os.path.join(config.PROFILE_DIR, config.last_selected_profile)
        # try:
        #     with open(profile_path, 'r') as f:
        #         loaded_data = json.load(f)
        #         if loaded_data.get('type') == 'profile' and 'data' in loaded_data:
        #             self.profile = loaded_data
        #         else:
        #             logger.warning(f"Invalid profile format in {config.last_selected_profile}")
        # except Exception as e:
        #     logger.error(f"Failed to load profile {config.last_selected_profile}: {e}")
        #     self.profile = {"name": "Error Loading", "data": [[0,0]]}


    def on_enter(self):
        """Called when switching to this screen."""
        self.load_profile_data()
        self.draw()

    def update(self, data):
        """Redraw diagram if relevant data changes (e.g., selected profile)."""
        # Could check if config.last_selected_profile changed
        # For now, redraw on any update when active
        if self.ui.current_screen == self:
             # Potentially reload profile if it might have changed
             # self.load_profile_data() # Uncomment if needed, might be inefficient
             self.draw()

    def draw(self, mode="tab_bar"): # Add mode parameter
        """Draws the profile diagram or tab bar representation."""
        if mode == "tab_bar":
            # Tab bar drawing is handled by MenuUI calling TabBar component
            pass # Do nothing here

        # --- Full Screen Diagram Drawing ---
        display = self.ui.display
        font = display.font_small # Use the small font loaded by display

        if not self.profile or not self.profile.get("data") or len(self.profile["data"]) < 2:
            display.draw_lines([
                "Diagram",
                "",
                "No valid profile data",
                "to display.",
                "",
                "Hold: Back"
            ])
            return

        profile_name = self.profile.get("name", "Unnamed Profile")
        data = self.profile["data"] # List of [time_sec, temp_c]

        # Screen space for plotting (adjust margins as needed)
        margin_top = 12 # Space for title
        margin_bottom = 5
        margin_left = 4
        margin_right = 4
        plot_w = display.width - margin_left - margin_right
        plot_h = display.height - margin_top - margin_bottom

        # Get data ranges
        try:
            times = [pt[0] for pt in data]
            temps = [pt[1] for pt in data]
            min_t, max_t = min(times), max(times)
            min_y, max_y = min(temps), max(temps)
            # Add a small buffer to temp range if min/max are the same
            if max_y == min_y: max_y += 1
            if max_t == min_t: max_t += 1 # Avoid division by zero
        except (TypeError, IndexError, ValueError) as e:
             logger.error(f"Error processing profile data points: {e}")
             display.draw_lines(["Diagram", "", "Error in profile data.", "", "Hold: Back"])
             return


        # Scaling functions (time -> x, temp -> y)
        # Y=0 is at the top, so we invert the scaling
        def scale_x(t): return int(margin_left + ((t - min_t) / (max_t - min_t)) * plot_w)
        def scale_y(y): return int(display.height - margin_bottom - ((y - min_y) / (max_y - min_y)) * plot_h)

        # Create list of scaled (x, y) points
        points = [(scale_x(t), scale_y(y)) for t, y in data]

        # Use the display's custom drawing function
        def draw_fn(draw):
            # Draw Title
            draw.text((margin_left, 1), profile_name[:20], font=font, fill="white") # Limit title length

            # Draw Axes (optional, basic lines)
            # draw.line([(margin_left, margin_top), (margin_left, display.height - margin_bottom)], fill="gray") # Y-axis
            # draw.line([(margin_left, display.height - margin_bottom), (display.width - margin_right, display.height - margin_bottom)], fill="gray") # X-axis

            # Draw Profile Line
            if len(points) >= 2:
                draw.line(points, fill="white", width=1)

            # Draw Points (optional)
            # for (x, y) in points:
            #     draw.ellipse((x - 1, y - 1, x + 1, y + 1), outline="white", fill="black")

        display.draw_custom(draw_fn)


    def enter_screen(self):
        """Short press on tab enters the diagram view."""
        self.load_profile_data() # Ensure data is fresh
        self.draw(mode="submenu") # Draw the full diagram
        return "enter_submenu" # Tell MenuUI we are now at level 1

    def handle_event(self, event):
        """Handles events when DiagramScreen is active (level > 0)."""
        # Long press is handled globally to go back up a level.
        # Short press or rotation could potentially interact with the diagram in the future (e.g., show point details)
        # For now, they do nothing in this screen.
        pass

    def on_exit(self):
        """Clean up if needed."""
        self.profile = None # Clear loaded data
        logger.debug("[DiagramScreen] Exited.")
