# ui/screens/screen_base.py
import logging

logger = logging.getLogger(__name__)

class UIScreen:
    """Base class for all main UI screens."""
    def __init__(self, ui_manager):
        self.ui = ui_manager
        # Make display accessible easily, assuming ui_manager has it
        self.display = ui_manager.display if hasattr(ui_manager, 'display') else None
        if not self.display:
             logger.error(f"[{self.__class__.__name__}] Display object not found in ui_manager!")
        self.last_kiln_data = {} # Initialize for data comparison


    def on_enter(self):
        """
        Called by MenuUI when this screen becomes the *current_screen*.
        This happens when switching tabs (level 0) or when returning focus
        after a modal component is popped (if this screen was the caller).
        """
        logger.debug(f"[{self.__class__.__name__}] on_enter (Level: {self.ui.current_screen_level})")
        # Default implementation: redraw based on current level
        mode = "tab_bar" if self.ui.current_screen_level == 0 else "submenu"
        # Don't redraw here directly, let redraw_current_view handle it after switch
        # self.draw(mode=mode)


    def on_submenu_enter(self):
        """
        Optional: Called specifically when the screen transitions from level 0
        (tab bar) to level 1 (active submenu/screen focus) via short press.
        Useful for setup needed only when entering the interactive mode.
        """
        logger.debug(f"[{self.__class__.__name__}] on_submenu_enter")
        # Default: Just draw in submenu mode
        # self.draw(mode="submenu") # Redraw is handled by MenuUI after transition


    def enter_screen(self):
         """
         Optional: Called by MenuUI on short press when the screen is at level 0 (tab bar).
         The screen can decide if it wants to enter a submenu state.
         Return "enter_submenu" to transition to level 1.
         Return "context_pushed" if the screen pushed a component itself.
         Return None or any other value to stay at level 0.
         """
         logger.debug(f"[{self.__class__.__name__}] enter_screen called")
         # Default behavior: transition to level 1
         # self.draw(mode="submenu") # Redraw handled by MenuUI
         return "enter_submenu"


    def on_exit(self):
        """
        Called by MenuUI just before switching *away* from this screen
        to make another screen the *current_screen*.
        Not called when just pushing/popping modal components *over* this screen.
        """
        logger.debug(f"[{self.__class__.__name__}] on_exit")
        pass

    def handle_event(self, event):
        """
        Handle rotary events ('rot_left', 'rot_right', 'short_press')
        when this screen has focus (level > 0) and *no modal component* is active.
        Long press is typically handled globally by MenuUI to go back.
        If the event causes a visual change, this method should call self.ui.redraw_current_view().
        """
        logger.debug(f"[{self.__class__.__name__}] handle_event({event}) - Level {self.ui.current_screen_level}")
        pass # Default: do nothing

    def update(self, kiln_data):
        """
        Receive updated kiln data from MenuUI (forwarded from observer).
        Called periodically or when data changes.
        Subclasses should implement logic to compare kiln_data with self.last_kiln_data
        and call self.ui.redraw_current_view() ONLY if a visual update is needed.
        Remember to update self.last_kiln_data after processing.
        """
        # logger.debug(f"[{self.__class__.__name__}] update received data")
        # Default: Do nothing, expect subclasses to implement comparison and redraw trigger
        pass


    def draw(self, mode="submenu"):
         """
         Draw the screen's content onto the display buffer.
         Args:
             mode (str): "tab_bar" if the screen is just the highlighted tab,
                         "submenu" if the screen has focus (level > 0).
         Implementation should handle drawing appropriately for the mode.
         This method should typically clear the area it needs (or expect MenuUI/Display to clear first)
         and draw its content. It does NOT directly trigger the physical display update.
         """
         logger.warning(f"[{self.__class__.__name__}] draw(mode={mode}) - Not implemented!")
         if self.display:
              # It's safer for draw methods to clear before drawing their content
              # Or rely on redraw_current_view to clear first. Let's assume redraw clears.
              # self.display.clear() # Avoid clear here, let redraw_current_view handle it
              error_lines = [f"{self.__class__.__name__}", f"(Mode: {mode})", "Draw Not Implemented"]
              self.display.draw_lines(error_lines[:self.display.rows])
