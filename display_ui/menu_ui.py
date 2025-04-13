# --- START OF FILE: display_ui/menu_ui.py ---
import logging
from lib.base_observer import BaseObserver # Assuming lib is accessible
from display_ui.screens import build_screens
# Import TabBar component
try:
    from display_ui.screens.component_screens.tab_bar import TabBar
except ImportError:
    logging.error("Failed to import TabBar component!")
    TabBar = None # Define as None if import fails

logger = logging.getLogger(__name__)

class MenuUI(BaseObserver):
    """
    Handles screen state, input navigation, hierarchy, and modal components.
    Receives kiln data via .send() and forwards it to the active screen.
    Implements global navigation logic using hierarchy levels and active input context.
    Special handling for Overview screen display.
    """

    def __init__(self, display):
        """Initializes the MenuUI manager."""
        super().__init__(observer_type="ui")
        self.display = display
        self.kiln_data = {} # Stores the latest received kiln data

        # Build and store all *main* screen instances
        self.screens = build_screens(display, self)

        # Create TabBar instance
        self.tab_bar_component = TabBar(self) if TabBar else None
        if not self.tab_bar_component:
             logger.error("TabBar component failed to initialize.")

        # --- Global State Initialization ---
        self.current_screen_name = "overview" # Start at the overview screen
        self.current_screen = self.screens.get(self.current_screen_name)
        if self.current_screen is None: # Safety check
            raise ValueError(f"Default screen '{self.current_screen_name}' not found!")

        # Start Overview at Level 1 conceptually, others at 0
        self.current_screen_level = 1 if self.current_screen_name == "overview" else 0
        self.current_tab_index = 0     # Index within the *allowed* tabs list
        self.active_input_context = None # For modal components
        # --- End Global State ---

        # Initial screen setup call and draw
        if hasattr(self.current_screen, "on_enter"):
            self.current_screen.on_enter()
        self.redraw_current_view() # Ensure initial state is shown
        logger.info("MenuUI initialized.")

    def get_allowed_tabs(self):
        """Returns list of screen keys allowed in the tab bar based on state."""
        state = self.kiln_data.get("state", "IDLE").upper()
        if state in {"RUNNING", "PAUSED"}:
            return ["overview", "diagram"]
        else:
            # Deactivated screens are commented out
            return [
                "overview",
                "diagram",
                "profile_selector",
                # "manual_control",
                # "profile_builder",
                # "settings"
            ]

    def send(self, data):
        """Receives data and forwards it to the active view's update method."""
        if not isinstance(data, dict): return
        self.kiln_data = data.copy()
        target_view = self.active_input_context.get('component') if self.active_input_context else self.current_screen
        if target_view and hasattr(target_view, "update"):
            try:
                target_view.update(self.kiln_data)
            except Exception as e:
                logger.error(f"Error calling update() on {type(target_view).__name__}: {e}", exc_info=True)

    def handle_rotary_event(self, event):
        """Routes input events based on current context and level."""
        logger.debug(f"Event: {event}, Level: {self.current_screen_level}, Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}")

        # 1. Active Component Handles Input First
        if self.active_input_context:
            component = self.active_input_context.get('component')
            if component and hasattr(component, "handle_event"):
                try: component.handle_event(event)
                except Exception as e: logger.error(f"Error in component {type(component).__name__}.handle_event: {e}", exc_info=True)
            else: logger.error("Active context component invalid or missing handle_event!")
            return # Event consumed by component

        # 2. Handle Based on Level (No Active Component)
        redraw_needed = False
        screen_result = None
        tabs = self.get_allowed_tabs() # Get tabs list once
        if not tabs: return # Safety check

        # --- Case A: Overview Screen is Active (Conceptually Level 1) ---
        if self.current_screen_level == 1 and self.current_screen_name == "overview":
            logger.debug("Handling event for Overview Screen (L1)")
            if hasattr(self.current_screen, "handle_event"):
                try:
                    screen_result = self.current_screen.handle_event(event)
                except Exception as e:
                    logger.error(f"Error in {self.current_screen_name}.handle_event: {e}", exc_info=True)
            else:
                logger.warning("Overview screen missing handle_event method!")

            # Check if Overview requested switch_and_enter (for rot_right)
            if isinstance(screen_result, tuple) and len(screen_result) == 2 and screen_result[0] == "switch_and_enter":
                target_screen_name = screen_result[1]
                logger.info(f"Handling switch_and_enter request from Overview to {target_screen_name}")
                # Switch screen (level will be set based on target by _internal_switch_to)
                self._internal_switch_to(target_screen_name, level=0)
                new_screen = self.screens.get(target_screen_name)
                # Attempt to enter the new screen's submenu immediately
                if new_screen and hasattr(new_screen, "enter_screen"):
                    enter_result = new_screen.enter_screen()
                    if enter_result == "enter_submenu":
                        self.current_screen_level = 1 # Ensure level is 1 after entering
                        logger.debug(f"Immediately entered submenu for {target_screen_name}")
                redraw_needed = True
                screen_result = None # Mark as handled

            elif screen_result == "context_pushed":
                pass # Redraw handled by push_context

            # If event was rot_left, pop_context_or_level was called by Overview's handler,
            # which sets level=0 and triggers redraw. No further action needed here.

        # --- Case B: Tab Bar is Active (Level 0) for screens OTHER than Overview ---
        elif self.current_screen_level == 0:
            logger.debug(f"Handling event for Tab Bar (L0), Current Tab: {self.current_screen_name}")
            original_tab_index = self.current_tab_index

            # Handle Rotation
            if event == "rot_left":
                self.current_tab_index = (self.current_tab_index - 1 + len(tabs)) % len(tabs)
            elif event == "rot_right":
                self.current_tab_index = (self.current_tab_index + 1) % len(tabs)

            # Handle Short Press (Enter Screen Submenu)
            elif event == "short_press":
                if hasattr(self.current_screen, "enter_screen"):
                    try:
                        screen_result = self.current_screen.enter_screen()
                        if screen_result == "enter_submenu":
                            self.current_screen_level = 1; redraw_needed = True
                        # context_pushed handled by push_context
                    except Exception as e:
                        logger.error(f"Error in {self.current_screen_name}.enter_screen: {e}", exc_info=True)
                else: # Default enter submenu
                    self.current_screen_level = 1; redraw_needed = True

            # Handle Long Press (Go back to Overview)
            elif event == "long_press":
                # Long press on non-overview tab goes to overview
                logger.debug("Long press on Tab Bar -> Switching to Overview")
                self._internal_switch_to("overview", level=0) # _internal sets level to 1
                redraw_needed = True

            # If Rotation Changed Tab -> Switch Screen Internally
            if event in ("rot_left", "rot_right") and self.current_tab_index != original_tab_index:
                 self._internal_switch_to(tabs[self.current_tab_index], level=0) # Handles overview level set
                 redraw_needed = True

        # --- Case C: Submenu Active (Level > 0) for screens OTHER than Overview ---
        else:
            logger.debug(f"Handling event for Screen {self.current_screen_name} Submenu (L{self.current_screen_level})")
            if event == "long_press":
                self.pop_context_or_level() # Pop component or return to Level 0 Tab Bar
            elif hasattr(self.current_screen, "handle_event"):
                try:
                    # Let the screen handle other events in its submenu state
                    screen_result = self.current_screen.handle_event(event)
                    # Could potentially handle switch_and_enter here too if needed
                except Exception as e:
                    logger.error(f"Error in {self.current_screen_name}.handle_event: {e}", exc_info=True)
            else:
                 logger.warning(f"Screen {self.current_screen_name} has no handle_event for Level {self.current_screen_level}")

        # --- Trigger Redraw if needed ---
        if redraw_needed and not self.active_input_context and screen_result != "context_pushed":
             self.redraw_current_view()

    def _internal_switch_to(self, new_screen_name, level):
        """Internal helper to switch the main `current_screen`."""
        target_screen = self.screens.get(new_screen_name)
        if not target_screen:
            logger.warning(f"Unknown screen: {new_screen_name}"); return

        # Avoid redundant actions if already on the target screen unless level changes
        if new_screen_name == self.current_screen_name and \
           not (new_screen_name == "overview" and self.current_screen_level == 0 and level == 0) and \
           self.current_screen_level == level:
             # logger.debug(f"Already on screen {new_screen_name} at level {level}. No switch.")
             # Still call on_enter for potential resets when switching tabs at level 0
             if level == 0 and hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
             return

        # Call exit hook on the old screen
        if self.current_screen and hasattr(self.current_screen, "on_exit"):
            # Don't call exit on self if just changing level (e.g., Overview 0->1)
            if not (new_screen_name == self.current_screen_name):
                try: self.current_screen.on_exit()
                except Exception as e: logger.error(f"Error in {self.current_screen_name}.on_exit: {e}", exc_info=True)

        logger.info(f"Switching to screen: {new_screen_name} requested at level {level}")

        previous_screen_name = self.current_screen_name
        self.current_screen_name = new_screen_name
        self.current_screen = target_screen
        self.active_input_context = None # Clear component context

        # --- Special Level Handling for Overview ---
        if new_screen_name == "overview": # Regardless of requested level
            self.current_screen_level = 1 # Overview display always means Level 1 interaction mode
            logger.debug("Switched to Overview, setting level to 1.")
        else:
            self.current_screen_level = level # Use requested level for other screens
        # --- End Special Handling ---

        # Update tab index
        try:
            tabs = self.get_allowed_tabs()
            self.current_tab_index = tabs.index(new_screen_name)
        except ValueError: pass # Not a tab screen

        # Call enter hook on the new screen
        if hasattr(self.current_screen, "on_enter"):
             try: self.current_screen.on_enter()
             except Exception as e: logger.error(f"Error in {self.current_screen_name}.on_enter: {e}", exc_info=True)

    def switch_to_screen(self, screen_name):
        """Public method for screens to switch main screen (goes to Level 0/1)."""
        logger.debug(f"Screen '{self.current_screen_name}' requested switch to '{screen_name}'")
        self._internal_switch_to(screen_name, level=0) # Request level 0, _internal handles Overview
        self.redraw_current_view() # Trigger redraw

    def push_context(self, mode, component, caller_screen_name, callback=None):
        """Pushes a modal component onto the view stack."""
        if not component: logger.error("push_context called with None component!"); return
        new_level = self.current_screen_level + 1
        self.active_input_context = {'mode': mode,'component': component,'caller': caller_screen_name,'callback': callback,'level': new_level}
        self.current_screen_level = new_level
        logger.debug(f"Pushed context: {mode}, Caller: {caller_screen_name}, Level now {self.current_screen_level}")
        if hasattr(component, "on_enter"): component.on_enter()
        self.redraw_current_view() # Show the new component

    def pop_context(self):
        """Pops the currently active modal component."""
        if not self.active_input_context: logger.warning("pop_context called but no active context!"); return
        mode = self.active_input_context.get('mode'); caller_name = self.active_input_context.get('caller')
        caller_level = self.active_input_context.get('level', 1) - 1
        logger.debug(f"Popping context: {mode}, Returning to level {caller_level}")

        self.active_input_context = None; self.current_screen_level = max(0, caller_level)

        # Ensure current_screen matches caller (usually they are the same)
        if caller_name and caller_name != self.current_screen_name:
            logger.warning(f"Popping context - caller '{caller_name}' differs from current screen '{self.current_screen_name}'.")
            # Only switch back if caller exists and level makes sense
            if caller_name in self.screens and self.current_screen_level > 0:
                 self._internal_switch_to(caller_name, self.current_screen_level)

        # Call on_enter for the screen/component regaining focus
        view_to_reactivate = self.current_screen
        if view_to_reactivate and hasattr(view_to_reactivate, "on_enter"): view_to_reactivate.on_enter()

        self.redraw_current_view() # Redraw view below popped context

    def pop_context_or_level(self):
         """Handles back action (long press)."""
         if self.active_input_context:
              component = self.active_input_context.get('component')
              if component and hasattr(component, "handle_event"): component.handle_event("long_press")
              else: logger.debug("Component lacks long_press handler, forcing pop."); self.pop_context()
         elif self.current_screen_level > 0: # In a submenu (including Level 1 Overview)
              logger.debug(f"Returning to tab bar from level {self.current_screen_level}")
              self.current_screen_level = 0 # Go back to tab bar level
              if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
              self.redraw_current_view() # Redraw needed to show tab bar (or overview if now selected)
         # No action needed if already at level 0

    def redraw_current_view(self):
        """Determines what to draw based on state and calls the draw method."""
        if not self.display or not self.display._buffer: return
        logger.info(f"[MenuUI] Redrawing view - Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}, Level: {self.current_screen_level}")

        target_to_draw = None
        is_component = bool(self.active_input_context)

        if is_component:
            target_to_draw = self.active_input_context.get('component')
        else:
            target_to_draw = self.current_screen

        try:
            if is_component:
                # Draw Active Component
                if target_to_draw and hasattr(target_to_draw, "draw"):
                    logger.debug(f"Drawing component: {type(target_to_draw).__name__}")
                    target_to_draw.draw()
                else: logger.warning("Active component invalid/not drawable."); self.display.draw_lines(["Err: Bad Component"], clear_first=True)

            elif self.current_screen_level == 0:
                # Draw Standard Tab Bar (Overview is handled by Level 1 case now)
                logger.debug(f"Drawing TabBar for screen: {self.current_screen_name}")
                if self.tab_bar_component: self.tab_bar_component.draw()
                else: logger.error("TabBar component unavailable!"); self.display.draw_lines(["Err: No TabBar"], clear_first=True)

            else: # Level >= 1 (Draw Screen's Full/Submenu View)
                if target_to_draw and hasattr(target_to_draw, "draw"):
                    logger.debug(f"Drawing screen full/submenu: {type(target_to_draw).__name__}")
                    target_to_draw.draw(mode="submenu") # Pass mode for consistency
                else: logger.warning(f"Screen {type(target_to_draw).__name__} not drawable."); self.display.draw_lines(["Err: Bad Screen"], clear_first=True)

        except Exception as e:
            logger.exception(f"Error during draw processing: {e}")
            try: self.display.draw_lines(["Draw Error:", type(target_to_draw).__name__], clear_first=True)
            except Exception: pass

        # Commit buffer to display AFTER drawing is complete
        self.display.show()

# --- END OF FILE: display_ui/menu_ui.py ---