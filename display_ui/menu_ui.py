# --- START OF FILE: display_ui/menu_ui.py ---
import logging
from lib.base_observer import BaseObserver
from display_ui.screens import build_screens
from display_ui.screens.component_screens.tab_bar import TabBar # Import the new component

logger = logging.getLogger(__name__)

class MenuUI(BaseObserver):
    # ... (__init__ remains the same) ...
    def __init__(self, display):
        super().__init__(observer_type="ui"); self.display = display; self.kiln_data = {}
        self.screens = build_screens(display, self); self.tab_bar_component = TabBar(self)
        self.current_screen_name = "overview"; self.current_screen = self.screens[self.current_screen_name]
        self.current_screen_level = 0; self.current_tab_index = 0; self.active_input_context = None
        if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
        self.redraw_current_view(); logger.info("MenuUI initialized.")
    def get_allowed_tabs(self):
        state = self.kiln_data.get("state", "IDLE").upper()
        if state in {"RUNNING", "PAUSED"}: return ["overview", "diagram"]
        else: return ["overview", "diagram", "profile_selector"] # Deactivated others
    def send(self, data):
        if not isinstance(data, dict): return
        self.kiln_data = data.copy()
        target_component = self.active_input_context.get('component') if self.active_input_context else self.current_screen
        if target_component and hasattr(target_component, "update"): target_component.update(self.kiln_data)


    def handle_rotary_event(self, event):
        """Routes input events based on current context (modal component or screen)."""
        logger.debug(f"[MenuUI] Event: {event}, Level: {self.current_screen_level}, Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}")

        # 1. Handle Active Component Input
        if self.active_input_context:
            component = self.active_input_context.get('component')
            if component and hasattr(component, "handle_event"): component.handle_event(event)
            else: logger.error("[MenuUI] Active context exists but component or handler is missing!")
            return

        # 2. Handle Input Based on Hierarchy Level (No Active Component)
        redraw_needed = False

        # --- Level 0: Tab Bar Navigation ---
        if self.current_screen_level == 0:
            tabs = self.get_allowed_tabs()
            if not tabs: return
            original_tab_index = self.current_tab_index

            if event == "rot_left":
                self.current_tab_index = (self.current_tab_index - 1 + len(tabs)) % len(tabs)
            elif event == "rot_right":
                # --- REMOVED Special handling for Overview -> Diagram ---
                self.current_tab_index = (self.current_tab_index + 1) % len(tabs)
            elif event == "short_press":
                # Let the current screen handle the press action
                if hasattr(self.current_screen, "enter_screen"):
                    result = self.current_screen.enter_screen()
                    # Check result to see if we need to change level or if context was pushed
                    if result == "enter_submenu":
                         self.current_screen_level = 1
                         logger.debug(f"Entered submenu {self.current_screen_name}")
                         redraw_needed = True # Need redraw to show submenu
                    elif result == "context_pushed":
                         pass # push_context handled redraw
                    else: # Result was None or other, stay at Level 0
                         pass
                else:
                     # Default action: Go to Level 1 (unlikely needed now)
                     logger.warning(f"Screen {self.current_screen_name} has no enter_screen, attempting default level change.")
                     self.current_screen_level = 1
                     redraw_needed = True
            elif event == "long_press":
                if self.current_screen_name != "overview":
                    if "overview" in tabs: self.current_tab_index = tabs.index("overview")
                    else: self.current_tab_index = 0
                    self._internal_switch_to("overview", level=0)
                    redraw_needed = True

            # If tab index changed due to rotation, switch screen and mark for redraw
            if event in ("rot_left", "rot_right") and self.current_tab_index != original_tab_index:
                 self._internal_switch_to(tabs[self.current_tab_index], level=0)
                 redraw_needed = True

        # --- Level > 0: Submenu Navigation ---
        else: # Should only happen if a screen other than Overview enters level > 0
            if event == "long_press":
                self.pop_context_or_level() # Handles redraw
            elif hasattr(self.current_screen, "handle_event"):
                self.current_screen.handle_event(event) # Screen handles events/redraw

        # Redraw IF needed and safe
        if redraw_needed and not self.active_input_context:
             self.redraw_current_view()

    # ... (_internal_switch_to, switch_to_screen, push_context, pop_context, pop_context_or_level remain the same) ...
    def _internal_switch_to(self, new_screen_name, level):
        if new_screen_name == self.current_screen_name and self.current_screen_level == level:
             if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter(); return
        if new_screen_name not in self.screens: logger.warning(f"Unknown screen: {new_screen_name}"); return
        if self.current_screen and hasattr(self.current_screen, "on_exit"): self.current_screen.on_exit()
        logger.info(f"Switching to screen: {new_screen_name} at level {level}")
        self.current_screen_name = new_screen_name; self.current_screen = self.screens[new_screen_name]
        self.current_screen_level = level; self.active_input_context = None
        try: tabs = self.get_allowed_tabs(); self.current_tab_index = tabs.index(new_screen_name)
        except ValueError: pass
        if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
    def switch_to_screen(self, screen_name):
        logger.debug(f"Screen '{self.current_screen_name}' requested switch to '{screen_name}'")
        self._internal_switch_to(screen_name, level=0); self.redraw_current_view()
    def push_context(self, mode, component, caller_screen_name, callback=None):
        new_level = self.current_screen_level + 1
        self.active_input_context = {'mode': mode,'component': component,'caller': caller_screen_name,'callback': callback,'level': new_level}
        self.current_screen_level = new_level; logger.debug(f"Pushed context: {mode}, Level now {self.current_screen_level}")
        if hasattr(component, "on_enter"): component.on_enter()
        self.redraw_current_view()
    def pop_context(self):
        if not self.active_input_context: logger.warning("pop_context called but no active context!"); return
        caller_name = self.active_input_context.get('caller'); caller_level = self.active_input_context.get('level', 1) - 1
        mode = self.active_input_context.get('mode'); logger.debug(f"Popping context: {mode}, Returning to level {caller_level}")
        self.active_input_context = None; self.current_screen_level = max(0, caller_level)
        if caller_name and caller_name != self.current_screen_name: logger.warning(f"Popping context - caller '{caller_name}' differs from current '{self.current_screen_name}'.")
        if self.current_screen and hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
        self.redraw_current_view()
    def pop_context_or_level(self):
         if self.active_input_context:
              component = self.active_input_context.get('component')
              if component and hasattr(component, "handle_event"): component.handle_event("long_press") # Let component handle pop
              else: logger.debug("Component has no long_press handler, forcing pop."); self.pop_context()
         elif self.current_screen_level > 0:
              logger.debug(f"Returning to tab bar from level {self.current_screen_level}"); self.current_screen_level = 0
              if hasattr(self.current_screen, "on_enter"): self.current_screen.on_enter()
              self.redraw_current_view()
         else: # Already at level 0
             logger.debug("Long press at level 0, going to overview.")
             if self.current_screen_name != "overview": self._internal_switch_to("overview", level=0); self.redraw_current_view()

    # --- redraw_current_view Modified ---
    def redraw_current_view(self):
        """Draws the active component or screen TO THE BUFFER, then shows it."""
        if not self.display or not self.display._buffer:
             logger.warning("[MenuUI] Redraw requested but display buffer not available.")
             return

        logger.info(f"[MenuUI] Redrawing view - Context: {self.active_input_context is not None}, Screen: {self.current_screen_name}, Level: {self.current_screen_level}")

        target_to_draw = None
        is_component = False

        if self.active_input_context:
            target_to_draw = self.active_input_context.get('component')
            is_component = True
        else: # No active component
            target_to_draw = self.current_screen
            draw_mode = "tab_bar" if self.current_screen_level == 0 else "submenu"

        # --- Drawing Logic ---
        try:
            if is_component:
                # Draw the active component (e.g., ScrollableList, ConfirmScreen)
                if target_to_draw and hasattr(target_to_draw, "draw"):
                    logger.debug(f"Drawing component: {type(target_to_draw).__name__}")
                    target_to_draw.draw() # Components draw their full view
                else:
                     logger.warning(f"Active component {type(target_to_draw).__name__} has no draw method.")
                     self.display.draw_lines(["Error:", "Component", "No draw method"], clear_first=True)

            elif draw_mode == "tab_bar":
                # --- Special Case: Overview draws full screen, others use TabBar ---
                if self.current_screen_name == "overview":
                    logger.debug("Drawing Overview screen directly (Level 0)")
                    # Call Overview's draw method directly, it handles the full screen
                    target_to_draw.draw(mode="submenu") # Tell it to draw its full view
                else:
                    # Use the dedicated TabBar component for other screens at Level 0
                    logger.debug(f"Drawing TabBar for screen: {self.current_screen_name}")
                    self.tab_bar_component.draw()
                # --- End Special Case ---

            else: # draw_mode == "submenu" (Level > 0, no component active)
                # Draw the main screen's specific content when it has focus
                if target_to_draw and hasattr(target_to_draw, "draw"):
                     logger.debug(f"Drawing screen submenu: {type(target_to_draw).__name__}")
                     target_to_draw.draw(mode=draw_mode) # Screens handle their submenu view
                else:
                     logger.warning(f"Screen {type(target_to_draw).__name__} has no draw method for submenu.")
                     self.display.draw_lines(["Error:", f"{self.current_screen_name}", "No submenu draw"], clear_first=True)

        except Exception as e:
            logger.exception(f"Error during draw processing for {type(target_to_draw).__name__}: {e}")
            try: self.display.draw_lines(["Draw Error:", type(target_to_draw).__name__, "Check logs."], clear_first=True)
            except: pass

        # --- Commit buffer to display ---
        self.display.show()
        # --- End Drawing Logic ---


# --- END OF FILE: display_ui/menu_ui.py ---