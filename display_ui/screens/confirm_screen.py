# confirm_screen.py
from display_ui.screens.screen_base import UIScreen

class ConfirmScreen(UIScreen):
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self.message = ""
        self.on_yes = None
        self.on_no = None
        self.selected = 0  # 0 = YES, 1 = NO
        self.return_to = "overview"
   
    def set_context(self, message, on_yes, on_no=None, return_to="overview"):
        self.message = message
        self.on_yes = on_yes
        self.on_no = on_no
        self.selected = 0
        self.return_to = return_to

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
            self.ui.switch_to(self.return_to)

    def update(self, data):
        pass  # No kiln data needed here
