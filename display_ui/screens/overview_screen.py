# display_ui/screens/overview_screen.py

from display_ui.screens.screen_base import UIScreen

class OverviewScreen(UIScreen):
    def __init__(self, display, ui_manager):
        super().__init__(ui_manager)
        self.display = display

    def on_enter(self):
        self.draw()

    def update(self, data):
        self.draw()

    def draw(self):
        data = self.ui.kiln_data or {}
        temp = data.get("temperature", 0.0)
        target = data.get("target", 0.0)
        state = data.get("state", "IDLE").upper()
        profile = data.get("profile", "N/A")
        runtime = int(data.get("runtime", 0))

        action_label = "[ Pause ▶ ]" if state == "RUNNING" else "[ Stop ▶ ]" if state == "PAUSED" else ""

        lines = [
            "Kiln Overview",
            "",
            f"Now:    {temp:.1f}°C",
            f"Target: {target:.1f}°C",
            f"State:  {state}",
            f"Profile: {profile}",
            f"Time:   {runtime}s",
        ]

        if action_label:
            lines.append("")
            lines.append(action_label)

        self.display.draw_lines(lines)

    def handle_event(self, event):
        state = self.ui.kiln_data.get("state", "IDLE").upper()

        if event == "rot_left":
            self.ui.switch_to("diagram")

        elif event == "rot_right":
            # If oven is running or paused, go to stop/pause confirmation
            if state == "RUNNING":
                self.ui.screens["confirm"].set_context(
                    message="Pause the kiln?",
                    on_yes=lambda: print("✅ Pause confirmed"),  # replace with actual pause logic
                    on_no=lambda: self.ui.switch_to("overview")
                )
                self.ui.switch_to("confirm")

            elif state == "PAUSED":
                self.ui.screens["confirm"].set_context(
                    message="Stop the kiln?",
                    on_yes=lambda: print("🛑 Stop confirmed"),  # replace with stop logic
                    on_no=lambda: self.ui.switch_to("overview")
                )
                self.ui.switch_to("confirm")

        elif event == "short_press":
            # Same logic as rot_right in this case
            self.handle_event("rot_right")

        elif event == "long_press":
            pass  # could add more if needed
