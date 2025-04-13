# profile_builder_screen.py
from display_ui.screens.screen_base import UIScreen

class ProfileBuilderScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)

    def on_enter(self):
        self.draw()

    def draw(self):
        lines = [
            "Profile Builder (WIP)",
            "",
            "Future UI for editing",
            "firing curves & profiles.",
            "",
            "[ Return ]"
        ]
        self.ui.display.draw_lines(lines)

    def handle_event(self, event):
        if event in {"short_press", "long_press"}:
            return "tab_bar"
        return None

    def update(self, data):
        pass
