# ui/screens/screen_base.py

class UIScreen:
    def __init__(self, ui_manager):
        self.ui = ui_manager

    def on_enter(self):
        """Called when this screen becomes active."""
        pass

    def on_exit(self):
        """Called when we leave this screen."""
        pass

    def handle_event(self, event):
        """Handle rotary events: 'rot_left', 'rot_right', 'press', 'long_press'."""
        pass

    def update(self, kiln_data):
        """Receive updated kiln data from observer."""
        pass
