# --- START OF FILE: display_ui/menu_ui.py ---
import logging
from lib.base_observer import BaseObserver # Assuming this path is correct relative to project root
from display_ui.screens import build_screens
# Import TabBar component - Ensure the path is correct
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
    """

    def __init__(self, display):
        """Initializes the MenuUI manager."""
        super().__init__(observer_type="ui")
        self.display = display
        self.kiln_data = {} # Stores the latest received kiln data

        # Build and store all *main* screen instances defined in screens/__init__.py
        self.screens = build_screens(display, self)

        # Create TabBar instance only if the class was imported successfully
        self.tab_bar_component = TabBar(self) if TabBar else None
        if not self.tab_bar_component:
             logger.error("TabBar component failed to initialize.")

        # --- Global State Initialization ---
        self.current_screen_name = "overview" # Start at the overview screen
        self.current_screen = self.screens.get(self.current_screen_name)

        # Critical safety check: Ensure the default screen exists
        if self.current_screen is None:
            logger.error(f"Default screen '{self.current_screen_name}' not found in built screens!")
            # Attempt to fallback to the first available screen
            if self.screens:
                fallback_screen_name = list(self.screens.keys())[0]
                self.current_screen_name = fallback_screen_name
                self.current_screen = self.screens[fallback_screen_name]
                logger.warning(f"Falling back to first available screen: {fallback_screen_name}")
            else:
                # If no screens exist at all, this is a fatal configuration error
                raise ValueError("No screens were built! Cannot initialize MenuUI.")

        self.current_screen_level = 0  # 0: Tab Bar/Overview, 1: Submenu, 2+: Modals
        self.current_tab_index = 0     # Index within the *allowed* tabs list
        self.active_input_context = None # Stores info about active components (list, confirm, etc.)
        # --- End Global State ---

        # Initial screen setup call and draw
        if hasattr(self.current_screen, "on_enter"):
            self.current_screen.on_enter()
        self.redraw_current_view() # Ensure initial state is shown
        logger.info("MenuUI initialized.")

    def get_allowed_tabs(self):
        """
        Returns a list of screen keys allowed in the tab bar based on kiln state.
        Order in the returned list determines scrolling order.
        """
        state = self.kiln_data.get("state", "IDLE").upper()
        if state in {"RUNNING", "PAUSED"}:
            # Only allow Overview and Diagram when kiln is active
            return ["overview", "diagram"]
        else:
            # Tabs available when IDLE or in other states
            # Currently deactivated screens are commented out
            logger.debug("Kiln IDLE/other state, showing reduced tabs.")
            return [
                "overview",
                "diagram",
                "profile_selector",
                # "manual_control", # Deactivated
                # "profile_builder",# Deactivated
                # "settings"        # Deactivated
            ]

    def send(self, data):
        """
        Receives data (e.g., from kiln controller's observer pattern)
        and forwards it to the currently active view (screen or component)
        for potential updates.
        """
        if not isinstance(data, dict):
            logger.warning(f"[MenuUI] Received non-dict data: {type(data)}")
            return

        self.kiln_data = data.copy() # Store the latest data

        # Determine which part of the UI should receive the update
        target_view = None
        if self.active_input_context:
            target_view = self.active_input_context.get('component')
        else:
            target_view = self.current_screen

        # If the target view has an update method, call it
        if target_view and hasattr(target_view, "update"):
            try:
                target_view.update(self.kiln_data)
            except Exception as e:
                logger.error(f"Error calling update() on {type(target_view).__name__}: {e}", exc_info=True)
        # Note: The update method itself decides if a redraw is needed

    def handle_rotary_event(self, event):
        """
        Routes incoming rotary events (rot_left, rot_right, short_press, long_press)
        to the appropriate handler based on the current UI state (level, active component).
        """
        logger.debug(f"[MenuUI] Event: {event}, Level: {self.current_screen_level}, Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}")

        # --- 1. Active Component Handles Input ---
        if self.active_input_context:
            component = self.active_input_context.get('component')
            if component and hasattr(component, "handle_event"):
                try:
                    component.handle_event(event) # Component processes event
                except Exception as e:
                    logger.error(f"Error in component {type(component).__name__}.handle_event: {e}", exc_info=True)
            else:
                logger.error("[MenuUI] Active context component missing or has no handle_event method!")
            return # Event consumed by the component layer

        # --- 2. Handle Input Based on Hierarchy Level (No Active Component) ---
        redraw_needed = False     # Flag if navigation requires redraw
        screen_result = None    # To store return values from screen methods

        # --- Level 0: Tab Bar Navigation / Overview Actions ---
        if self.current_screen_level == 0:
            tabs = self.get_allowed_tabs()
            if not tabs:
                logger.warning("[MenuUI] No allowed tabs found!")
                return
            original_tab_index = self.current_tab_index

            # --- Handle Rotation ---
            if event == "rot_left":
                self.current_tab_index = (self.current_tab_index - 1 + len(tabs)) % len(tabs)
            elif event == "rot_right":
                self.current_tab_index = (self.current_tab_index + 1) % len(tabs)

            # --- Handle Short Press (Enter Screen / Overview Action) ---
            elif event == "short_press":
                if hasattr(self.current_screen, "enter_screen"):
                    try:
                        screen_result = self.current_screen.enter_screen()
                        if screen_result == "enter_submenu":
                            self.current_screen_level = 1 # Transition to submenu level
                            logger.debug(f"Entered submenu for {self.current_screen_name}")
                            # Notify screen if method exists (optional)
                            if hasattr(self.current_screen, "on_submenu_enter"):
                                self.current_screen.on_submenu_enter()
                            redraw_needed = True # Need redraw to show submenu
                        elif screen_result == "context_pushed":
                            # Screen pushed a component, redraw handled by push_context
                            pass
                        else:
                            # Screen handled press but didn't change level/context
                            logger.debug(f"Screen {self.current_screen_name} handled short_press at Level 0.")
                    except Exception as e:
                        logger.error(f"Error in {self.current_screen_name}.enter_screen: {e}", exc_info=True)
                else:
                    # Default action if screen has no specific enter_screen
                    logger.warning(f"Screen {self.current_screen_name} has no enter_screen method. Defaulting to level 1.")
                    self.current_screen_level = 1
                    redraw_needed = True

            # --- Handle Long Press (Go to Overview) ---
            elif event == "long_press":
                if self.current_screen_name != "overview":
                    logger.debug("Long press at Level 0 -> Switching to Overview")
                    try:
                        # Find overview index safely
                        overview_index = tabs.index("overview") if "overview" in tabs else 0
                        self.current_tab_index = overview_index
                        self._internal_switch_to("overview", level=0)
                        redraw_needed = True
                    except Exception as e:
                        logger.error(f"Error switching to overview on long press: {e}")

            # --- If Rotation Changed Tab -> Switch Screen Internally ---
            if event in ("rot_left", "rot_right") and self.current_tab_index != original_tab_index:
                 self._internal_switch_to(tabs[self.current_tab_index], level=0)
                 redraw_needed = True

        # --- Level > 0: Screen Submenu Navigation ---
        else:
            if event == "long_press":
                self.pop_context_or_level() # Handles its own redraw logic
            elif hasattr(self.current_screen, "handle_event"):
                try:
                    # Let the screen handle other events in its submenu state
                    screen_result = self.current_screen.handle_event(event)

                    # Check for special switch_and_enter result (e.g., from Overview -> Diagram)
                    if isinstance(screen_result, tuple) and len(screen_result) == 2 and screen_result[0] == "switch_and_enter":
                        target_screen_name = screen_result[1]
                        logger.info(f"[MenuUI] Handling switch_and_enter request to {target_screen_name}")
                        self._internal_switch_to(target_screen_name, level=0) # Switch screen first
                        new_screen = self.screens.get(target_screen_name)
                        if new_screen and hasattr(new_screen, "enter_screen"):
                            enter_result = new_screen.enter_screen() # Attempt to enter new screen
                            if enter_result == "enter_submenu":
                                self.current_screen_level = 1 # Set level correctly
                                logger.debug(f"Immediately entered submenu for {target_screen_name}")
                            # Context pushed case handled by push_context
                        redraw_needed = True # Redraw after switch/enter attempt
                        screen_result = None # Mark as handled

                except Exception as e:
                    logger.error(f"Error in {self.current_screen_name}.handle_event: {e}", exc_info=True)
            else:
                logger.warning(f"Screen {self.current_screen_name} has no handle_event method for level {self.current_screen_level}")

        # --- Trigger Redraw if Needed ---
        # Redraw if navigation caused a change, no component is active,
        # and redraw wasn't handled by pop_context or push_context.
        if redraw_needed and not self.active_input_context and screen_result != "context_pushed":
             self.redraw_current_view()

    def _internal_switch_to(self, new_screen_name, level):
        """
        Internal helper to switch the main `current_screen`.
        Updates state variables but does NOT trigger redraw itself.
        """
        # Avoid unnecessary switching to self at the same level
        if new_screen_name == self.current_screen_name and self.current_screen_level == level:
             if level == 0 and hasattr(self.current_screen, "on_enter"):
                 # Re-call on_enter if just switching tabs without level change
                 self.current_screen.on_enter()
             return

        target_screen = self.screens.get(new_screen_name)
        if not target_screen:
            logger.warning(f"Tried to switch to unknown screen: {new_screen_name}")
            return

        # Call exit hook on the old screen
        if self.current_screen and hasattr(self.current_screen, "on_exit"):
            try:
                self.current_screen.on_exit()
            except Exception as e:
                logger.error(f"Error in {self.current_screen_name}.on_exit: {e}", exc_info=True)

        logger.info(f"Switching to screen: {new_screen_name} at level {level}")
        self.current_screen_name = new_screen_name
        self.current_screen = target_screen
        self.current_screen_level = level
        self.active_input_context = None # Clear component context on main screen switch

        # Update tab index if it's a known tab
        try:
            tabs = self.get_allowed_tabs()
            self.current_tab_index = tabs.index(new_screen_name)
        except ValueError:
             logger.debug(f"Switched to {new_screen_name} which is not in current allowed tabs.")
             pass # Not an error

        # Call enter hook on the new screen
        if hasattr(self.current_screen, "on_enter"):
             try:
                self.current_screen.on_enter()
             except Exception as e:
                 logger.error(f"Error in {self.current_screen_name}.on_enter: {e}", exc_info=True)

    def switch_to_screen(self, screen_name):
        """Public method for screens to request switching to another main screen (at Level 0)."""
        logger.debug(f"Screen '{self.current_screen_name}' requested switch to '{screen_name}'")
        self._internal_switch_to(screen_name, level=0)
        self.redraw_current_view() # Trigger redraw after the switch

    def push_context(self, mode, component, caller_screen_name, callback=None):
        """Pushes a modal component (like a list or confirmation) onto the view stack."""
        if not component:
            logger.error("push_context called with None component!")
            return

        new_level = self.current_screen_level + 1
        self.active_input_context = {
            'mode': mode,
            'component': component,
            'caller': caller_screen_name,
            'callback': callback,
            'level': new_level
        }
        self.current_screen_level = new_level # Increase hierarchy depth
        logger.debug(f"Pushed context: {mode}, Caller: {caller_screen_name}, Level now {self.current_screen_level}")

        # Call component's on_enter if it exists
        if hasattr(component, "on_enter"):
            try:
                component.on_enter()
            except Exception as e:
                logger.error(f"Error in component {type(component).__name__}.on_enter: {e}", exc_info=True)

        self.redraw_current_view() # Redraw immediately to show the new component

    def pop_context(self):
        """Pops the currently active modal component, returning focus to the caller."""
        if not self.active_input_context:
            logger.warning("pop_context called but no active context!")
            return

        mode = self.active_input_context.get('mode')
        caller_name = self.active_input_context.get('caller')
        caller_level = self.active_input_context.get('level', 1) - 1 # Level below component
        logger.debug(f"Popping context: {mode}, Returning to level {caller_level}")

        # Clear the active context
        self.active_input_context = None
        self.current_screen_level = max(0, caller_level) # Restore previous level

        # Ensure the current_screen is still the one that called the context
        if caller_name and caller_name != self.current_screen_name:
             logger.warning(f"Popping context - caller '{caller_name}' differs from current screen '{self.current_screen_name}'. Check logic.")
             # Potentially switch back if needed, but usually indicates a logic flaw
             # if caller_name in self.screens: self._internal_switch_to(caller_name, self.current_screen_level)

        # Call on_enter for the screen/component regaining focus
        view_to_reactivate = self.current_screen # Assume screen regains focus
        # If popping reveals another component underneath (future enhancement?), adjust target
        # if self.active_input_context: view_to_reactivate = self.active_input_context.get('component')

        if view_to_reactivate and hasattr(view_to_reactivate, "on_enter"):
            try:
                view_to_reactivate.on_enter()
            except Exception as e:
                logger.error(f"Error calling on_enter for {type(view_to_reactivate).__name__} after pop: {e}", exc_info=True)

        # Redraw the view that is now active
        self.redraw_current_view()

    def pop_context_or_level(self):
         """Handles back action (long press): pops component or returns to tab bar."""
         if self.active_input_context:
              # If a component is active, let it handle long press
              component = self.active_input_context.get('component')
              if component and hasattr(component, "handle_event"):
                   component.handle_event("long_press") # Component should call pop_context
              else:
                  # Default pop if component doesn't handle long press
                  logger.debug("Component has no long_press handler, forcing pop.")
                  self.pop_context()
         elif self.current_screen_level > 0:
              # If in a screen's submenu, return to tab bar (Level 0)
              logger.debug(f"Returning to tab bar from level {self.current_screen_level}")
              self.current_screen_level = 0
              if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
              self.redraw_current_view()
         else:
              # Already at Level 0, long press goes to Overview (if not already there)
              logger.debug("Long press at level 0, switching to overview.")
              if self.current_screen_name != "overview":
                  self._internal_switch_to("overview", level=0)
                  self.redraw_current_view()

    def redraw_current_view(self):
        """
        Determines what needs to be drawn based on current state
        (level, active component) and calls the appropriate draw method.
        Finally, commits the buffer to the physical display.
        """
        if not self.display or not hasattr(self.display, '_buffer') or not self.display._buffer:
             logger.warning("[MenuUI] Redraw requested but display buffer not available.")
             return

        logger.info(f"[MenuUI] Redrawing view - Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}, Level: {self.current_screen_level}")

        target_to_draw = None
        is_component = bool(self.active_input_context)

        if is_component:
            target_to_draw = self.active_input_context.get('component')
        else:
            target_to_draw = self.current_screen
            # Determine if we should show TabBar or full Overview screen
            is_tab_bar_mode = (self.current_screen_level == 0 and self.current_screen_name != "overview")

        # --- Drawing Logic ---
        try:
            if is_component:
                # Draw the active component
                if target_to_draw and hasattr(target_to_draw, "draw"):
                    logger.debug(f"Drawing component: {type(target_to_draw).__name__}")
                    target_to_draw.draw() # Components draw their full view
                else:
                    logger.warning(f"Active component {type(target_to_draw).__name__} has no draw method.")
                    self.display.draw_lines(["Error:", "Component", "No draw"], clear_first=True)

            elif self.current_screen_level == 0:
                 # At Level 0: Draw Overview full screen or TabBar for others
                if self.current_screen_name == "overview":
                    logger.debug("Drawing Overview screen directly (Level 0)")
                    if target_to_draw and hasattr(target_to_draw, "draw"):
                        target_to_draw.draw(mode="submenu") # Use its full screen draw
                    else: logger.error("Overview screen object invalid/not drawable!")
                else:
                    # Draw standard tab bar for other screens at Level 0
                    logger.debug(f"Drawing TabBar for screen: {self.current_screen_name}")
                    if self.tab_bar_component:
                        self.tab_bar_component.draw()
                    else:
                        logger.error("TabBar component not available!")
                        self.display.draw_lines(["Error:", "No TabBar"], clear_first=True)

            else: # Level > 0, no component active -> Draw screen's submenu
                if target_to_draw and hasattr(target_to_draw, "draw"):
                     logger.debug(f"Drawing screen submenu: {type(target_to_draw).__name__}")
                     target_to_draw.draw(mode="submenu") # Screens handle their submenu view
                else:
                     logger.warning(f"Screen {type(target_to_draw).__name__} has no draw method for submenu.")
                     self.display.draw_lines(["Error:", f"{self.current_screen_name}", "No submenu draw"], clear_first=True)

        except Exception as e:
            logger.exception(f"Error during draw processing for {type(target_to_draw).__name__}: {e}")
            # Attempt to draw error message to screen as fallback
            try:
                self.display.draw_lines(["Draw Error:", type(target_to_draw).__name__, "Check logs."], clear_first=True)
            except Exception: pass # Avoid recursive errors

        # --- Commit buffer to display ---
        try:
            self.display.show()
        except Exception as e:
            logger.error(f"Error calling display.show(): {e}")
        # --- End Drawing Logic ---

# --- END OF FILE: display_ui/menu_ui.py ---