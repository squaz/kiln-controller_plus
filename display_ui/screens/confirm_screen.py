# --- START OF FILE: display_ui/screens/confirm_screen.py ---
import logging
from display_ui.screens.screen_base import UIScreen

logger = logging.getLogger(__name__)

class ConfirmScreen(UIScreen):
    # ... (__init__, set_context, on_enter, draw remain the same) ...
    def __init__(self, ui_manager):
        super().__init__(ui_manager)
        self.message = ""; self.on_yes = None; self.on_no = None
        self.selected_option = 0
    def set_context(self, message, on_yes, on_no=None):
        self.message = message; self.on_yes = on_yes; self.on_no = on_no
        self.selected_option = 0
    def on_enter(self): pass
    def draw(self, mode=None):
        if not self.display: return
        margin_x = 5; button_y_offset = self.display.line_height_small + 4
        max_message_lines = self.display.rows - 3
        wrapped_lines = self.display.wrap_text(self.message, self.display.font_small, self.display.width - 2 * margin_x)
        lines_to_draw = wrapped_lines[:max_message_lines]
        final_lines = [""] * self.display.rows; current_line_index = 1
        for line in lines_to_draw:
            if current_line_index < self.display.rows - 2: final_lines[current_line_index] = f" {line}"; current_line_index += 1
            else: break
        button_line_index = self.display.rows - 2; hint_line_index = self.display.rows - 1
        yes_text = "→ YES" if self.selected_option == 0 else "  YES"
        no_text = "→ NO" if self.selected_option == 1 else "  NO"
        final_lines[button_line_index] = f"  {yes_text}   {no_text}"
        final_lines[hint_line_index] = " Hold: Cancel (NO)"
        self.display.draw_lines(final_lines, clear_first=True)

    def handle_event(self, event):
        if event == "rot_left" or event == "rot_right":
            self.selected_option = 1 - self.selected_option
            self.ui.redraw_current_view()
        elif event == "short_press":
            # --- Reverted: Pop context AFTER queuing action ---
            action_to_call = None
            if self.selected_option == 0: # YES
                if callable(self.on_yes): action_to_call = self.on_yes
                else: logger.warning("ConfirmScreen: YES but no callback.")
            else: # NO
                if callable(self.on_no): action_to_call = self.on_no
                else: logger.debug("ConfirmScreen: NO, no callback.")

            self.ui.pop_context() # Pop confirm screen context first

            if action_to_call: # Execute the action AFTER popping
                logger.debug(f"ConfirmScreen: Executing {'YES' if self.selected_option == 0 else 'NO'} action.")
                action_to_call()
            # --- End Reverted ---
        elif event == "long_press":
             # --- Reverted: Pop context AFTER queuing action ---
             logger.debug("ConfirmScreen: Long press treated as NO.")
             action_to_call = None
             if callable(self.on_no): action_to_call = self.on_no

             self.ui.pop_context() # Pop first

             if action_to_call:
                 logger.debug("ConfirmScreen: Executing NO action (from long press).")
                 action_to_call()
             # --- End Reverted ---

    def update(self, data): pass

# --- END OF FILE: display_ui/screens/confirm_screen.py ---