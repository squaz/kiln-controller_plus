#display_screen.py ---
import logging
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont # Need Image, ImageDraw
import math

logger = logging.getLogger(__name__)

class KilnDisplay:
    """
    Singleton for controlling the ST7735 (or other) display via luma.lcd.
    Provides draw_* methods for different screens. Calculates usable rows.
    Includes helper for partial text updates.
    """
    _instance = None
    DEFAULT_LINE_HEIGHT_SMALL = 14
    DEFAULT_LINE_HEIGHT_LARGE = 16

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self.config = config
        self.width = config.get('width', 160)
        self.height = config.get('height', 128)
        self.bg_color = "black" # Define background color

        # Load fonts
        font_path = config.get('font_path', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        font_small_size = config.get('font_small_size', 11)
        font_large_size = config.get('font_large_size', 13)
        try:
            self.font_small = ImageFont.truetype(font_path, font_small_size)
            self.font_large = ImageFont.truetype(font_path, font_large_size)
            self.line_height_small = config.get('line_height_small', self.DEFAULT_LINE_HEIGHT_SMALL)
            self.line_height_large = config.get('line_height_large', self.DEFAULT_LINE_HEIGHT_LARGE)

        except Exception as e:
            logger.warning(f"[KilnDisplay] Could not load custom fonts: {e}")
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.line_height_small = self.DEFAULT_LINE_HEIGHT_SMALL
            self.line_height_large = self.DEFAULT_LINE_HEIGHT_LARGE

        usable_height = self.height - config.get('vertical_margin', 0)
        self.rows = usable_height // self.line_height_small
        logger.info(f"[KilnDisplay] Calculated usable rows: {self.rows} (Height: {self.height}, LineHeight: {self.line_height_small})")

        # Initialize SPI device
        try:
            serial = spi(
                port=config.get('spi_port', 0),
                device=config.get('spi_device', 1),
                gpio_DC=config.get('gpio_dc', 13),
                gpio_RST=config.get('gpio_rst', 19),
                bus_speed_hz=config.get('spi_bus_speed_hz', 8000000)
            )
            self.device = st7735(
                serial,
                rotate=config.get('rotate', 0),
                width=self.width,
                height=self.height,
                bgr=config.get('bgr', True)
            )
            # Create a buffer for partial updates
            self._buffer = Image.new("RGB", (self.width, self.height), self.bg_color)
            self._draw_buffer = ImageDraw.Draw(self._buffer)

            self.clear() # Clear display buffer on init
            self.show() # Show cleared display
            logger.info("[KilnDisplay] ST7735 display initialized.")
        except Exception as e:
            logger.error(f"[KilnDisplay] Hardware SPI init failed: {e}")
            self.device = None
            self._buffer = None
            self._draw_buffer = None

    @classmethod
    def get_instance(cls, config=None):
         # Simplified get_instance logic from previous version
        if cls._instance is None:
            if config is None:
                try:
                    import config as proj_config # Assuming config.py exists
                    config_data = proj_config.DISPLAY_CONFIG
                    logger.info("[KilnDisplay] Loaded display config from default config.py")
                except (ImportError, AttributeError):
                     raise ValueError("First call to KilnDisplay requires a config dict, or DISPLAY_CONFIG in config.py.")
            else:
                 config_data = config
            cls._instance = cls(config_data)
        return cls._instance


    def _commit_buffer(self):
        """Sends the internal buffer to the physical display."""
        if self.device and self._buffer:
            try:
                self.device.display(self._buffer)
            except Exception as e:
                logger.error(f"[KilnDisplay] Error committing buffer to device: {e}")
        elif not self.device:
             logger.warning("[KilnDisplay] Commit buffer called but device not available.")


    def clear(self):
        """Clears the internal buffer and optionally the display."""
        if not self._draw_buffer or not self._buffer:
            logger.warning("[KilnDisplay] Clear called but buffer not available.")
            return
        self._draw_buffer.rectangle((0, 0, self.width, self.height), fill=self.bg_color)
        # Don't necessarily need to commit here, subsequent draws will

    def show(self):
         """Explicitly commit the current buffer state to the display."""
         self._commit_buffer()

    def wrap_text(self, text, font, max_width):
        """Wraps text (unchanged)."""
        lines = []
        words = text.split()
        if not words: return []
        current_line = words[0]
        for word in words[1:]:
            test_line = f"{current_line} {word}"
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

    def draw_lines(self, lines, x_offset=2, start_y=0, clear_first=True):
        """
        Draws multiple lines onto the internal buffer.
        """
        if not self._draw_buffer: return
        if clear_first:
             self.clear()

        y = start_y
        for i, line in enumerate(lines):
            if i >= self.rows and start_y == 0: # Basic bounds check if starting at top
                logger.warning(f"[KilnDisplay] Too many lines ({len(lines)}) for display ({self.rows} rows). Truncating.")
                break
            try:
                self._draw_buffer.text((x_offset, y), str(line), font=self.font_small, fill="white")
            except Exception as e:
                 logger.error(f"Error drawing line '{line}': {e}")
            y += self.line_height_small
        # self._commit_buffer() # Don't commit automatically, let caller decide


    def update_text_line(self, line_index, text, x_offset=2, line_height=None, font=None):
        """
        Updates a specific line of text by drawing background then new text.
        Assumes line_index is 0-based.
        """
        if not self._draw_buffer or not self._buffer: return
        if font is None: font = self.font_small
        if line_height is None: line_height = self.line_height_small

        y_pos = line_index * line_height
        # Bounding box for clearing: full width, specific height
        # Add small vertical padding if needed, but line_height should suffice
        clear_bbox = (0, y_pos, self.width, y_pos + line_height)

        try:
            # logger.debug(f"Updating line {line_index} at y={y_pos} with text: {text}")
            # 1. Clear the area on the buffer
            self._draw_buffer.rectangle(clear_bbox, fill=self.bg_color)
            # 2. Draw the new text onto the buffer
            self._draw_buffer.text((x_offset, y_pos), str(text), font=font, fill="white")
            # 3. Commit the change (important for partial update to be seen)
            # self._commit_buffer() # Let caller decide when to commit
        except Exception as e:
            logger.error(f"Error in update_text_line for line {line_index}: {e}")


    def draw_custom(self, draw_fn, clear_first=True):
        """
        Give low-level drawing access via a callback TO THE BUFFER.
        """
        if not self._draw_buffer: return
        if clear_first:
             self.clear()
        try:
            # Pass the buffer's draw object to the function
            draw_fn(self._draw_buffer)
            # self._commit_buffer() # Let caller decide
        except Exception as e:
             logger.error(f"[KilnDisplay] Error during draw_custom: {e}")


    def draw_confirm(self, message, selected_index=0):
        """ Draw confirmation dialog TO THE BUFFER. """
        if not self._draw_buffer: return
        self.clear() # Confirm usually needs full redraw

        margin_x = 5
        margin_y = 2
        button_y_offset = self.line_height_small + 4
        wrapped_lines = self.wrap_text(message, self.font_small, self.width - 2 * margin_x)
        y = margin_y
        lines_drawn = 0
        max_message_lines = self.rows - 2
        for line in wrapped_lines:
            if lines_drawn >= max_message_lines: break
            self._draw_buffer.text((margin_x, y), line, font=self.font_small, fill="white")
            y += self.line_height_small
            lines_drawn += 1

        button_y = self.height - button_y_offset
        yes_text = "→ YES" if selected_index == 0 else "  YES"
        no_text = "→ NO" if selected_index == 1 else "  NO"
        self._draw_buffer.text((margin_x + 10, button_y), yes_text, font=self.font_small, fill="white")
        self._draw_buffer.text((self.width // 2 + 10, button_y), no_text, font=self.font_small, fill="white")

        # self._commit_buffer() # Let caller decide
