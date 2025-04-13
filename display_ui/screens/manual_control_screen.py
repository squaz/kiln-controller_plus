# manual_control_screen.py
import logging
from display_ui.screens.screen_base import UIScreen
from display_ui.screens.component_screens.value_input_screen import ValueInputScreen # Import component

logger = logging.getLogger(__name__)

class ManualControlScreen(UIScreen):
    def __init__(self, ui):
        super().__init__(ui)
        self.target_temp = 150
        self.hold_time_minutes = 5
        self.selection_index = 0  # 0 = temp, 1 = hold, 2 = start, 3 = return
        self.options = ["Target Temp:", "Time to Hold:", "[ Start Heat ▶ ]", "[ Return ]"]
        self.value_input_component = None # Placeholder

    def on_enter(self):
        """Called when switching to this screen in tab mode."""
        self.draw(mode="tab_bar")

    def enter_screen(self):
        """Called by MenuUI when short press occurs on this tab."""
        self.selection_index = 0 # Reset selection on entering
        self.draw(mode="submenu") # Draw the full control view
        return "enter_submenu" # Tell MenuUI we are now at level 1

    def on_submenu_enter(self):
         """Called by MenuUI when screen becomes level 1 focus."""
         self.draw(mode="submenu")

    def draw(self, mode="tab_bar"):
        """Draws the screen content based on mode."""
        # Tab bar drawing is handled by MenuUI calling TabBar component
        pass # Do nothing here

        # --- Full Screen Manual Control Drawing ---
        lines = [
            "Manual Heat Control",
            "",
            f"{'→' if self.selection_index == 0 else ' '} {self.options[0]:<15} {self.target_temp}°C",
            f"{'→' if self.selection_index == 1 else ' '} {self.options[1]:<15} {self.hold_time_minutes}m",
            "",
            f"{'→' if self.selection_index == 2 else ' '} {self.options[2]}",
            f"{'→' if self.selection_index == 3 else ' '} {self.options[3]}"
        ]
        self.display.draw_lines(lines)

    def handle_event(self, event):
        """Handles events when ManualControlScreen is active (level > 0) and no component is pushed."""
        if event == "rot_right":
            self.selection_index = (self.selection_index + 1) % len(self.options)
            self.draw(mode="submenu")
        elif event == "rot_left":
            self.selection_index = (self.selection_index - 1) % len(self.options)
            self.draw(mode="submenu")
        elif event == "short_press":
            self._handle_short_press()
        # Long press is handled globally by MenuUI to pop level/context

    def _handle_short_press(self):
        """Handles action based on current selection."""
        selected_action = self.selection_index

        if selected_action == 0: # Edit Target Temp
            self._launch_value_input(
                label="Target Temp:",
                initial=self.target_temp,
                step=5, min_val=20, max_val=1300, unit="°C", # Adjust bounds as needed
                confirm_callback=self._confirm_temp
            )
        elif selected_action == 1: # Edit Hold Time
            self._launch_value_input(
                label="Time to Hold:",
                initial=self.hold_time_minutes,
                step=1, min_val=0, max_val=999, unit="m", # Adjust bounds as needed
                confirm_callback=self._confirm_hold
            )
        elif selected_action == 2: # Start Heat
            self._show_start_confirmation()
        elif selected_action == 3: # Return
             # Go back to tab bar level
             self.ui.pop_context_or_level() # Should reduce level from 1 to 0


    def _launch_value_input(self, label, initial, step, min_val, max_val, unit, confirm_callback):
        """Creates and pushes a ValueInputScreen component."""
        self.value_input_component = ValueInputScreen(
            ui_manager=self.ui,
            label=label,
            initial_value=initial,
            step=step, min_val=min_val, max_val=max_val, unit=unit,
            on_confirm_callback=confirm_callback,
            on_cancel_callback=self._cancel_input # Use a generic cancel handler
        )
        self.ui.push_context(
            mode="numeric_input",
            component=self.value_input_component,
            caller_screen_name="manual_control"
        )

    def _confirm_temp(self, new_temp):
        """Callback when temperature input is confirmed."""
        logger.debug(f"Temperature confirmed: {new_temp}")
        self.target_temp = int(new_temp) # Ensure it's int
        self.ui.pop_context() # Pop the value input component
        self.draw(mode="submenu") # Redraw manual control screen

    def _confirm_hold(self, new_hold):
        """Callback when hold time input is confirmed."""
        logger.debug(f"Hold time confirmed: {new_hold}")
        self.hold_time_minutes = int(new_hold) # Ensure it's int
        self.ui.pop_context() # Pop the value input component
        self.draw(mode="submenu") # Redraw manual control screen

    def _cancel_input(self):
        """Callback when value input is cancelled (long press)."""
        logger.debug("Value input cancelled.")
        self.ui.pop_context() # Pop the value input component
        self.draw(mode="submenu") # Redraw manual control screen

    def _show_start_confirmation(self):
        """Uses ConfirmScreen to ask user to start manual heating."""
        confirm_screen = self.ui.screens.get("confirm")
        if not confirm_screen:
             logger.error("ConfirmScreen not found!")
             return

        def yes_action():
            logger.info(f"🔥 Starting manual heat: Temp={self.target_temp}°C, Hold={self.hold_time_minutes}m")
            # === Add logic here to send command to kiln controller ===
            # self.ui.kiln_controller.start_manual(self.target_temp, self.hold_time_minutes * 60) # Example
            # =========================================================
            self.ui.pop_context() # Pop the confirm screen
            self.ui.switch_to_screen("overview") # Go to overview after starting

        def no_action():
            logger.debug("Manual start cancelled.")
            self.ui.pop_context() # Pop the confirm screen
            self.draw(mode="submenu") # Redraw manual control screen


        confirm_screen.set_context(
            message=f"Start heat to {self.target_temp}°C for {self.hold_time_minutes}m?",
            on_yes=yes_action,
            on_no=no_action
        )
        # Push the confirmation screen context
        self.ui.push_context(
            mode="confirm",
            component=confirm_screen,
            caller_screen_name="manual_control"
        )


    def update(self, data):
        """Update based on kiln data (e.g., state might change allowed tabs)."""
        if self.ui.current_screen_name == "manual_control" and self.ui.current_screen_level == 0:
             self.draw(mode="tab_bar")
        # No specific updates needed for the manual control parameters themselves based on kiln_data

    def on_exit(self):
         """Clean up when leaving the screen."""
         self.value_input_component = None # Release component instance
         logger.debug("[ManualControlScreen] Exited.")

