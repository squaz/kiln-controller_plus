# manual_control_screen.py
from display_ui.screens.screen_base import UIScreen

class ManualControlScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.target_temp = 150
        self.hold_time = 5  # in minutes
        self.selection = 0  # 0 = temp, 1 = hold, 2 = start, 3 = return
        self.max_selection = 3

    def on_enter(self):
        self.draw()

    def draw(self):
        lines = [
            "Manual Heat Control",
            "",
            f"Target Temp:     {'→' if self.selection == 0 else ' '} {self.target_temp}°C",
            f"Time to Hold:    {'→' if self.selection == 1 else ' '} {self.hold_time}m",
            "",
            f"{'[ Start Heat ▶ ]' if self.selection == 2 else '  Start Heat ▶  '}",
            f"{'[ Return ]' if self.selection == 3 else '  Return  '}"
        ]
        self.ui.display.draw_lines(lines)

    def handle_event(self, event):
        if event == "rot_right":
            self.selection = (self.selection + 1) % (self.max_selection + 1)
        elif event == "rot_left":
            self.selection = (self.selection - 1) % (self.max_selection + 1)
        elif event == "short_press":
            if self.selection == 0:
                self.target_temp = min(self.target_temp + 5, 999)
            elif self.selection == 1:
                self.hold_time = min(self.hold_time + 1, 999)
            elif self.selection == 2:
                self.ui.screens["confirm"].set_context(
                    message=f"Start heat to {self.target_temp}°C for {self.hold_time}m?",
                    on_confirm=lambda: print("🔥 Starting manual heat..."),  # Replace with actual start logic
                    on_cancel=lambda: self.ui.switch_to("manual_control")
                )
                return "confirm"
            elif self.selection == 3:
                return "tab_bar"

        self.draw()

    def update(self, data):
        # Optional: Update display if needed
        pass
