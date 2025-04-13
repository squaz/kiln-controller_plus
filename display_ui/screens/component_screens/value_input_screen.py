# display_ui/screens/component_screens/value_input_screen.py
import logging
import math

logger = logging.getLogger(__name__)

class ValueInputScreen:
    """
    A reusable component for editing a numeric value using rotary input.
    Handles value adjustments, bounds checking, and confirmation/cancellation.
    """
    def __init__(self, ui_manager, label, initial_value, step, min_val, max_val, unit="", on_confirm_callback=None, on_cancel_callback=None):
        """
        Args:
            ui_manager: The main MenuUI instance.
            label: Text prompt (e.g., "Target Temp").
            initial_value: Starting numeric value.
            step: Increment/decrement amount per rotary step.
            min_val: Minimum allowed value.
            max_val: Maximum allowed value.
            unit: Optional unit string (e.g., "°C", "m") to display after the value.
            on_confirm_callback: function(confirmed_value) called on short press.
            on_cancel_callback: function() called on long press.
        """
        self.ui = ui_manager
        self.display = ui_manager.display
        self.label = label
        self.current_value = initial_value
        self.step = step
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.on_confirm_callback = on_confirm_callback
        self.on_cancel_callback = on_cancel_callback

        # Store initial value in case of cancellation
        self._initial_value = initial_value

    def on_enter(self):
        """Called by MenuUI when this component becomes active."""
        self.draw()

    def handle_event(self, event):
        """Handles rotary events delegated by MenuUI."""
        value_changed = False
        if event == "rot_right":
            self.current_value += self.step
            # Clamp to max value, ensuring step doesn't accidentally skip max_val
            if self.current_value > self.max_val:
                self.current_value = self.max_val
            value_changed = True
        elif event == "rot_left":
            self.current_value -= self.step
            # Clamp to min value
            if self.current_value < self.min_val:
                self.current_value = self.min_val
            value_changed = True
        elif event == "short_press":
            if callable(self.on_confirm_callback):
                # Round to avoid floating point issues if step is integer
                if isinstance(self.step, int) and isinstance(self.current_value, float):
                    confirmed_value = round(self.current_value)
                else:
                    confirmed_value = self.current_value
                self.on_confirm_callback(confirmed_value)
            else:
                logger.warning("[ValueInputScreen] Short press occurred but no on_confirm_callback defined.")
                # Default behavior: Pop context even without callback
                self.ui.pop_context()
            return # Event handled
        elif event == "long_press":
            if callable(self.on_cancel_callback):
                self.on_cancel_callback()
            else:
                # Default behavior: Pop context on long press if no cancel callback
                logger.debug("[ValueInputScreen] No cancel callback, popping context on long press.")
                self.ui.pop_context()
            return # Event handled

        if value_changed:
            self.draw()

    def draw(self):
        """Draws the value input interface."""
        # Format value: Show integer if step is integer, else 1 decimal place
        if isinstance(self.step, int) and self.current_value == math.floor(self.current_value):
             value_str = f"{int(self.current_value)}{self.unit}"
        else:
             value_str = f"{self.current_value:.1f}{self.unit}"

        lines = [
            self.label,
            "",
            f"   → {value_str}", # Arrow indicates the editable value
            "",
            "Press: Confirm",
            "Hold: Cancel"
        ]
        self.display.draw_lines(lines)

    def update(self, data):
        """Placeholder for potential future updates based on external data."""
        pass # Not typically needed for this component
