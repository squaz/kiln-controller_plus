# confirm_screen.py
from display_ui.screens.screen_base import UIScreen

class ConfirmScreen(UIScreen):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self.message = ""
        self.on_yes = None
        self.on_no = None
        self.selected = 0  # 0 = YES, 1 = NO

    def set_context(self, message, on_yes, on_no=None):
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no
        self.selected = 0  # default to YES

    def on_enter(self):
        self.draw()

    def draw(self):
        if self.ui.display:
            self.ui.display.draw_confirm(self.message, self.selected)

    def handle_event(self, event):
        if event == "rot_left" or event == "rot_right":
            self.selected = 1 - self.selected  # toggle YES/NO
            self.draw()

        elif event == "short_press":
            if self.selected == 0 and callable(self.on_yes):
                self.on_yes()
            elif self.selected == 1 and callable(self.on_no):
                self.on_no()
            self.ui.switch_to("overview")  # Return to main view after decision

    def update(self, data):
        pass  # No kiln data needed here
