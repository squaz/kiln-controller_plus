# --- START OF FILE: display_ui/menu_ui.py ---
import logging
from lib.base_observer import BaseObserver  # Assuming lib is accessible
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
    Manages UI state, navigation, component lifecycle, and input routing.

    Coordinates interaction between Screens, Components (like TabBar,
    ScrollableList, ConfirmScreen), and the RotaryInput. Receives external
    data updates (e.g., kiln status) via the observer pattern.

    Special handling for Overview screen: It's treated as Level 1 immediately
    upon selection in the tab bar.
    """

class MenuUI(BaseObserver):
    """
    Manages UI state, navigation, component lifecycle, and input routing.
    Receives external data updates via the observer pattern.
    Can trigger actions in the main controller via callbacks.
    """

    # --- MODIFIED __init__ signature and body ---
    def __init__(self, display, action_callbacks=None):
        """
        Initializes the MenuUI manager.

        Args:
            display: The initialized KilnDisplay object.
            action_callbacks (dict, optional): Dictionary mapping action names
                                             ('start', 'pause', 'stop', 'resume') to
                                             functions in the main controller.
                                             Defaults to None.
        """
        super().__init__(observer_type="ui")
        self.display = display
        self.kiln_data = {} # Stores the latest received kiln data

        # Build and store all *main* screen instances
        # Pass self (ui_manager) to the build function now
        self.screens = build_screens(display, self)

        # Create TabBar instance
        self.tab_bar_component = TabBar(self) if TabBar else None
        if not self.tab_bar_component:
             logger.error("TabBar component failed to initialize.")

        # --- Store action callbacks ---
        self.action_callbacks = action_callbacks if isinstance(action_callbacks, dict) else {}
        if not self.action_callbacks:
            logger.warning("No action_callbacks provided to MenuUI. UI actions will only log.")
        # --- End store action callbacks ---

        # --- Global State Initialization ---
        self.current_screen_name = "overview"
        self.current_screen = self.screens.get(self.current_screen_name)
        if self.current_screen is None: # Safety check
            raise ValueError(f"Default screen '{self.current_screen_name}' not found!")

        # Start Overview at Level 1 conceptually, others at 0
        self.current_screen_level = 1 if self.current_screen_name == "overview" else 0
        self.current_tab_index = 0     # Index within the *allowed* tabs list
        self.active_input_context = None # Info about active modal components
        # --- End Global State ---

        # Initial screen setup call and draw
        if hasattr(self.current_screen, "on_enter"):
            try:
                 self.current_screen.on_enter()
            except Exception as e:
                 logger.error(f"Error during initial on_enter for {self.current_screen_name}: {e}", exc_info=True)
        self.redraw_current_view() # Ensure initial state is shown
        logger.info("MenuUI initialized.")

    def get_allowed_tabs(self):
        """Returns list of screen keys allowed in the tab bar based on state."""
        state = self.kiln_data.get("state", "IDLE").upper()
        if state in {"RUNNING", "PAUSED"}:
            return ["overview", "diagram"]
        else:
            # Currently active tabs when IDLE
            return [
                "overview",
                "diagram",
                "profile_selector",
                # "manual_control", # Deactivated
                # "profile_builder",# Deactivated
                # "settings"        # Deactivated
            ]

    def send(self, data):
        """Receives data and forwards it to the active view's update method."""
        logger.info(f"[MenuUI] Received data via send: State={data.get('state', 'N/A')}, Temp={data.get('temperature', 0.0):.1f}") 

        if not isinstance(data, dict):
            logger.warning(f"Received non-dict data: {type(data)}")
            return
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
                try:
                    component.handle_event(event)
                except Exception as e:
                    logger.error(f"Error in component {type(component).__name__}.handle_event: {e}", exc_info=True)
            else:
                logger.error("Active context component invalid or missing handle_event!")
            return # Event consumed

        # 2. Handle Based on Level (No Active Component)
        redraw_needed = False
        screen_result = None # Store results from screen handlers
        tabs = self.get_allowed_tabs()
        if not tabs: return

        # --- Combined Level 0 / Level 1 (Overview Special Case) Logic ---
        # This block handles navigation when no component is active.
        # It differentiates between the standard tab bar (Level 0 for non-Overview)
        # and the Overview screen's unique behavior (Level 1).

        original_tab_index = self.current_tab_index

        # Handle events differently depending on whether we are viewing the tab bar or a screen's submenu
        if self.current_screen_level == 0: # Standard Tab Bar Mode (for non-Overview screens)
            logger.debug(f"Handling event at Level 0 (Tab Bar), Current Tab: {self.current_screen_name}")

            if event == "rot_left":
                self.current_tab_index = (self.current_tab_index - 1 + len(tabs)) % len(tabs)
            elif event == "rot_right":
                self.current_tab_index = (self.current_tab_index + 1) % len(tabs)
            elif event == "short_press":
                if hasattr(self.current_screen, "enter_screen"):
                    screen_result = self.current_screen.enter_screen()
                    if screen_result == "enter_submenu":
                        self.current_screen_level = 1; redraw_needed = True
                    # context_pushed handled by push_context
                else: # Default action
                    self.current_screen_level = 1; redraw_needed = True
            elif event == "long_press":
                 # Should only happen if NOT on Overview (as it starts at L1)
                 if self.current_screen_name != "overview":
                    logger.debug("Long press on Tab Bar -> Switching to Overview")
                    self._internal_switch_to("overview", level=0); redraw_needed = True # _internal sets level 1

            # If rotation changed the tab, switch screen
            if event in ("rot_left", "rot_right") and self.current_tab_index != original_tab_index:
                 self._internal_switch_to(tabs[self.current_tab_index], level=0)
                 redraw_needed = True

        elif self.current_screen_level >= 1: # Submenu Mode (Level 1+ OR Overview's Level 1)
            logger.debug(f"Handling event at Level {self.current_screen_level} for screen {self.current_screen_name}")

            if event == "long_press":
                self.pop_context_or_level() # Handles own redraw
            elif hasattr(self.current_screen, "handle_event"):
                try:
                    # Let the specific screen's handler process the event
                    screen_result = self.current_screen.handle_event(event)

                    # --- Process special 'switch_and_enter' result ---
                    # This allows a screen (like Diagram) to request immediate entry into another screen
                    if isinstance(screen_result, tuple) and len(screen_result) == 2 and screen_result[0] == "switch_and_enter":
                        target_screen_name = screen_result[1]
                        logger.info(f"[MenuUI] Handling switch_and_enter request to {target_screen_name}")
                        # 1. Switch screen internally (level determined by _internal_switch_to)
                        self._internal_switch_to(target_screen_name, level=0)
                        # 2. Attempt to enter the new screen's submenu
                        new_screen = self.screens.get(target_screen_name)
                        if new_screen and hasattr(new_screen, "enter_screen"):
                            enter_result = new_screen.enter_screen()
                            if enter_result == "enter_submenu":
                                # Ensure level is 1 if we just entered a submenu
                                self.current_screen_level = 1
                                logger.debug(f"Immediately entered submenu for {target_screen_name}")
                            elif enter_result == "context_pushed":
                                logger.debug(f"{target_screen_name} pushed its own context on enter.")
                        redraw_needed = True # Redraw needed after switch/enter attempt
                        screen_result = None # Mark as handled
                    # --- End switch_and_enter processing ---

                except Exception as e:
                    logger.error(f"Error in {self.current_screen_name}.handle_event: {e}", exc_info=True)
            else:
                 logger.warning(f"Screen {self.current_screen_name} has no handle_event method for level {self.current_screen_level}")

        # --- Trigger Redraw if necessary ---
        if redraw_needed and not self.active_input_context and screen_result != "context_pushed":
             self.redraw_current_view()

    def _internal_switch_to(self, new_screen_name, level):
        """Internal helper to switch the main `current_screen`."""
        target_screen = self.screens.get(new_screen_name)
        if not target_screen:
            logger.warning(f"Unknown screen: {new_screen_name}"); return

        # Avoid redundant actions if already on the target screen AND level isn't changing meaningfully
        # Exception: Allow forcing redraw when switching between tabs at level 0
        needs_switch = True
        if new_screen_name == self.current_screen_name:
             is_overview_target = new_screen_name == "overview"
             target_level = 1 if is_overview_target else level # Determine target level
             if self.current_screen_level == target_level:
                  needs_switch = False
                  # Still call on_enter if just switching tabs at level 0
                  if level == 0 and hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()

        if not needs_switch: return # Exit if no real switch needed

        # Call exit hook on the old screen
        if self.current_screen and hasattr(self.current_screen, "on_exit"):
            if not (new_screen_name == self.current_screen_name): # Don't exit self if just changing level
                try: self.current_screen.on_exit()
                except Exception as e: logger.error(f"Error in {self.current_screen_name}.on_exit: {e}", exc_info=True)

        logger.info(f"Switching to screen: {new_screen_name} (requested level {level})")

        self.current_screen_name = new_screen_name
        self.current_screen = target_screen
        self.active_input_context = None # Clear component context

        # Set the correct level based on the target screen
        if new_screen_name == "overview":
            self.current_screen_level = 1 # Overview is always conceptually Level 1 when active
            logger.debug("Switched to Overview, level set to 1.")
        else:
            self.current_screen_level = level # Use requested level for others
            logger.debug(f"Switched to {new_screen_name}, level set to {level}.")

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
        logger.debug(f"Req switch to '{screen_name}'")
        self._internal_switch_to(screen_name, level=0) # Request level 0, _internal adjusts for Overview
        self.redraw_current_view()

    def push_context(self, mode, component, caller_screen_name, callback=None):
        """Pushes a modal component onto the view stack."""
        if not component: logger.error("push_context: None component!"); return
        new_level = self.current_screen_level + 1
        self.active_input_context = {
            'mode': mode,'component': component,'caller': caller_screen_name,
            'callback': callback,'level': new_level
        }
        self.current_screen_level = new_level
        logger.debug(f"Pushed context: {mode}, Caller: {caller_screen_name}, Level now {self.current_screen_level}")
        if hasattr(component, "on_enter"): component.on_enter()
        self.redraw_current_view() # Show the new component

    def pop_context(self):
        """Pops the currently active modal component."""
        if not self.active_input_context: logger.warning("pop_context: No active context!"); return
        mode = self.active_input_context.get('mode'); caller_name = self.active_input_context.get('caller')
        caller_level = self.active_input_context.get('level', 1) - 1
        logger.debug(f"Popping context: {mode}, Returning to level {caller_level}")

        self.active_input_context = None
        self.current_screen_level = max(0, caller_level) # Restore previous level

        # Ensure current_screen is correct after pop
        if caller_name and caller_name != self.current_screen_name:
            logger.warning(f"Popping context - caller '{caller_name}' differs from current '{self.current_screen_name}'.")
            # Generally assume current_screen remains correct unless explicitly switched

        # Call on_enter for the view regaining focus
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
              logger.debug(f"Returning to tab bar view from level {self.current_screen_level}")
              self.current_screen_level = 0 # Go back to Level 0
              # Find the index of the current screen in the allowed tabs
              try:
                  tabs = self.get_allowed_tabs()
                  self.current_tab_index = tabs.index(self.current_screen_name)
              except ValueError:
                  self.current_tab_index = 0 # Fallback to first tab
              # Call on_enter for the screen that will now be displayed in tab mode
              if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
              self.redraw_current_view() # Redraw needed to show tab bar (or overview if now selected)

    def redraw_current_view(self):
        """Determines what to draw based on state and calls the draw method."""
        if not self.display or not hasattr(self.display, '_buffer') or not self.display._buffer:
             logger.warning("[MenuUI] Redraw requested but display buffer not available.")
             return

        logger.info(f"[MenuUI] Redrawing view - Screen: {self.current_screen_name}, Level: {self.current_screen_level}, Context: {self.active_input_context is not None}")

        target_to_draw = None
        is_component = bool(self.active_input_context)

        if is_component:
            target_to_draw = self.active_input_context.get('component')
        else:
            target_to_draw = self.current_screen

        # --- Drawing Logic ---
        try:
            if is_component:
                # Draw the active component (e.g., ScrollableList, ConfirmScreen)
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
                    # Pass mode="submenu" for screens that might use it, Overview ignores it now
                    target_to_draw.draw(mode="submenu")
                else: logger.warning(f"Screen {type(target_to_draw).__name__} not drawable."); self.display.draw_lines(["Err: Bad Screen"], clear_first=True)

        except Exception as e:
            logger.exception(f"Error during draw processing: {e}")
            try: self.display.draw_lines(["Draw Error:", type(target_to_draw).__name__], clear_first=True)
            except Exception: pass

        # --- Commit buffer to display ---
        try:
            self.display.show()
        except Exception as e:
             logger.exception(f"Error during draw processing: {e}")

# --- END OF FILE: display_ui/menu_ui.py ---