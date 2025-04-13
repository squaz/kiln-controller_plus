# display_ui/screens/diagram_screen.py
from display_ui.screens.screen_base import UIScreen

class DiagramScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        # Sample profile data — replace with dynamic one later
        self.profile = {
            "type": "profile",
            "name": "cone-05-fast-bisque",
            "data": [
                [0, 65],
                [600, 200],
                [2088, 250],
                [5688, 250],
                [23135, 1733],
                [28320, 1888],
                [30900, 1888],
            ]
        }

    def on_enter(self):
        self.draw()

    def update(self, data):
        self.draw()

    def draw(self):
        display = self.ui.display
        font = display.font_small
        profile = self.profile
        data = profile["data"]

        # Screen space
        margin = 4
        plot_w = display.width - 2 * margin
        plot_h = display.height - 30  # Leave room at top for title

        # Normalize time (x) and temp (y)
        times = [pt[0] for pt in data]
        temps = [pt[1] for pt in data]

        min_t, max_t = min(times), max(times)
        min_y, max_y = min(temps), max(temps)

        def scale_x(t): return int(margin + (t - min_t) / (max_t - min_t) * plot_w)
        def scale_y(y): return int(display.height - margin - ((y - min_y) / (max_y - min_y) * plot_h))

        points = [(scale_x(t), scale_y(y)) for t, y in data]

        def draw_fn(draw):
            draw.text((5, 2), profile["name"], font=font, fill="white")
            for (x, y) in points:
                draw.ellipse((x - 1, y - 1, x + 1, y + 1), outline="white")  # draw points
            draw.line(points, fill="white", width=1)

        display.draw_custom(draw_fn)

    def handle_event(self, event):
        if event in ("short_press", "long_press"):
            return "tab_bar"
        return None
