# profile_selector_screen.py
from display_ui.screens.screen_base import UIScreen

class ProfileSelectorScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.profiles = ["Profile 1", "Profile 2", "Profile 3"]
        self.index = 0

    def on_enter(self):
        self.draw()

    def draw(self):
        lines = ["Select Profile:"]
        for i, name in enumerate(self.profiles):
            marker = "→" if i == self.index else "  "
            lines.append(f"{marker} {name}")
        lines.append("")
        lines.append("[ Return ]")
        self.ui.display.draw_lines(lines)

    def handle_event(self, event):
        if event == "rot_right":
            self.index = (self.index + 1) % len(self.profiles)
        elif event == "rot_left":
            self.index = (self.index - 1) % len(self.profiles)
        elif event == "short_press":
            print(f"✅ Selected: {self.profiles[self.index]}")
        elif event == "long_press":
            return "tab_bar"
        self.draw()

    def update(self, data):
        pass
