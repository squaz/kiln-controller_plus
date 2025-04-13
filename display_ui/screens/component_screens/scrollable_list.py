# --- START OF FILE: display_ui/screens/component_screens/scrollable_list.py ---
import logging

logger = logging.getLogger(__name__)

class ScrollableList:
    # ... (__init__, on_enter, _adjust_offset remain the same as previous 'fixed' version) ...
    def __init__(self, ui_manager, items, visible_count, title="", initial_selection=0, on_select_callback=None, on_cancel_callback=None):
        self.ui = ui_manager
        self.display = ui_manager.display
        self.items = items if items else []
        default_vc = 4
        if self.display and hasattr(self.display, 'rows') and self.display.rows > 1:
             self.visible_count = max(1, self.display.rows - (1 if title else 0))
        else: self.visible_count = visible_count if visible_count else default_vc
        self.title = title
        self.on_select_callback = on_select_callback
        self.on_cancel_callback = on_cancel_callback
        self.total_items = len(self.items)
        self.selection_index = min(max(0, initial_selection), self.total_items - 1) if self.total_items > 0 else 0
        self.offset = 0
        self._adjust_offset()

    def on_enter(self): pass

    def _adjust_offset(self):
        if self.total_items == 0: self.offset = 0; return
        max_offset = max(0, self.total_items - self.visible_count)
        if self.selection_index >= self.offset + self.visible_count: self.offset = self.selection_index - self.visible_count + 1
        elif self.selection_index < self.offset: self.offset = self.selection_index
        self.offset = max(0, min(self.offset, max_offset))

    def handle_event(self, event):
        """Handles rotary events delegated by MenuUI."""
        if self.total_items == 0:
             if event == "long_press": self.ui.pop_context() # Just pop if empty
             return

        original_index = self.selection_index
        redraw_needed = False # Track if state change requires redraw

        if event == "rot_right":
            self.selection_index = (self.selection_index + 1) % self.total_items
        elif event == "rot_left":
            self.selection_index = (self.selection_index - 1 + self.total_items) % self.total_items
        elif event == "short_press":
            # Don't pop here, let callback decide
            if callable(self.on_select_callback):
                selected_item = self.items[self.selection_index]
                self.on_select_callback(self.selection_index, selected_item)
            else: logger.warning("[ScrollableList] Short press, no callback.")
            return # Callback handles next step
        elif event == "long_press":
            # Default long press: pop context, then call cancel callback if exists
            cb = self.on_cancel_callback
            self.ui.pop_context() # Pop first
            if callable(cb): cb()
            return # Event handled

        # If rotation happened and index changed
        if event in ("rot_right", "rot_left") and self.selection_index != original_index:
             self._adjust_offset()
             redraw_needed = True

        # If state changed, redraw the component
        if redraw_needed:
             # self.draw() # Draw the changes to the buffer
             # self.ui.display.show() # Explicitly show buffer changes for component redraw
             # OR rely on MenuUI redraw (might be cleaner)
             self.ui.redraw_current_view()


    def draw(self, mode=None): # mode is ignored
        """Draws the list onto the display buffer."""
        # ... (Draw logic remains the same as previous correct version) ...
        if not self.display: return
        lines = []
        start_row = 0
        if self.title: lines.append(self.title); start_row = 1
        list_rows_available = self.display.rows - start_row
        items_to_show_count = min(self.visible_count, list_rows_available)
        if not self.items: lines.append("  (No items)")
        else:
            end_index = min(self.offset + items_to_show_count, self.total_items)
            visible_items_indices = range(self.offset, end_index)
            for i in visible_items_indices:
                item = self.items[i]; marker = "→" if i == self.selection_index else " "
                lines.append(f"{marker} {str(item)}")
        while len(lines) < self.display.rows: lines.append("")
        self.display.draw_lines(lines, clear_first=True)

    def update(self, data): pass

# --- END OF FILE: display_ui/screens/component_screens/scrollable_list.py ---