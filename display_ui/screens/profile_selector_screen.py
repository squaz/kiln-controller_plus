import os
import json
from display_ui.screens.screen_base import UIScreen
import settings_manager
import config  # uses proxy class to include dynamic settings

class ProfileSelectorScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.selection = 0
        self.profiles = []  # List of (filename, profile_name)

    def on_enter(self):
        self.load_profiles()
        self.draw()

    def load_profiles(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "storage", "profiles")
        )

        if not os.path.isdir(base_dir):
            self.profiles = []
            return

        files = [f for f in os.listdir(base_dir) if f.endswith(".json")]
        profiles = []

        for filename in sorted(files):
            try:
                with open(os.path.join(base_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("type") == "profile":
                        name = data.get("name", filename)
                        profiles.append((filename, name))
            except Exception as e:
                print(f"[ProfileSelector] Failed to load {filename}: {e}")

        self.profiles = profiles

        # Set selection to previously selected profile, if exists
        last = config.last_selected_profile
        for i, (filename, _) in enumerate(self.profiles):
            if filename == last:
                self.selection = i
                break
        else:
            self.selection = 0

    def draw(self):
        lines = ["Select Profile:"]
        for i, (_, name) in enumerate(self.profiles):
            marker = "→" if i == self.selection else "  "
            lines.append(f"{marker} {name}")

        # Return option
        is_return = (self.selection == len(self.profiles))
        lines.append("")
        lines.append("→ [ Return ]" if is_return else "   [ Return ]")

        self.ui.display.draw_lines(lines)

    def handle_event(self, event):
        total_items = len(self.profiles) + 1  # +1 for Return

        if event == "rot_right":
            self.selection = (self.selection + 1) % total_items
        elif event == "rot_left":
            self.selection = (self.selection - 1) % total_items

        elif event == "short_press":
            if self.selection == len(self.profiles):
                return "tab_bar"  # Return selected

            selected_file, selected_name = self.profiles[self.selection]

            self.ui.screens["confirm"].set_context(
                message=f"Set '{selected_name}' as current?",
                on_yes=lambda: self._confirm_selected(selected_file, selected_name),
                on_no=None,
                return_to="profile_selector"
            )
            return "confirm"

        elif event == "long_press":
            return "tab_bar"

        self.draw()

    def _confirm_selected(self, filename, name):
        print(f"✅ Selected profile: {name} ({filename})")
        config.last_selected_profile = filename
        self.ui.enter_tab_bar()

    def update(self, data):
        pass
