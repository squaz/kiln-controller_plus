# settings_screen.py
from display_ui.screens.screen_base import UIScreen

class SettingsScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.index = 0
        self.options = ["WiFi Config (F)", "General Settings", "Return"]

    def on_enter(self):
        self.draw()

    def draw(self):
        lines = ["Settings:"]
        for i, opt in enumerate(self.options):
            marker = "→" if i == self.index else "  "
            lines.append(f"{marker} {opt}")
        self.ui.display.draw_lines(lines)

    def handle_event(self, event):
        if event == "rot_right":
            self.index = (self.index + 1) % len(self.options)
        elif event == "rot_left":
            self.index = (self.index - 1) % len(self.options)
        elif event == "short_press":
            if self.options[self.index] == "Return":
                return "tab_bar"
        elif event == "long_press":
            return "tab_bar"
        self.draw()
        return None

    def update(self, data):
        pass
