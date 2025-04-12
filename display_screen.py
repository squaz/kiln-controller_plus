# display_screen.py
import logging
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw
import socket

logger = logging.getLogger(__name__)

class KilnDisplay:
    """
    Singleton for controlling the ST7735 (or other) display via luma.lcd.
    Provides draw_* methods for different screens.
    """
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config):
        # Prevent re-initializing if we've already set up
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self.config = config
        self.width = config.get('width', 160)
        self.height = config.get('height', 128)

        # Load fonts
        font_path = config.get('font_path', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        try:
            self.font_small = ImageFont.truetype(font_path, config.get('font_small_size', 11))
            self.font_large = ImageFont.truetype(font_path, config.get('font_large_size', 13))
        except Exception as e:
            logger.warning(f"[KilnDisplay] Could not load custom fonts: {e}")
            # fallback to default
            from PIL import ImageFont
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

        # Initialize hardware SPI
        try:
            serial = spi(
                port=0,
                device=1,               # Adjust if your CS line is CE0 or CE1
                gpio_DC=13,             # Matches config or your wiring
                gpio_RST=19,            # Matches config or your wiring
                bus_speed_hz=4000000
            )
            self.device = st7735(
                serial,
                rotate=config.get('rotate', 0),
                width=self.width,
                height=self.height,
                bgr=config.get('bgr', False)
            )
            logger.info("[KilnDisplay] ST7735 display initialized.")
        except Exception as e:
            logger.error(f"[KilnDisplay] Hardware SPI init failed: {e}")
            self.device = None

    @classmethod
    def get_instance(cls, config=None):
        if cls._instance is None:
            if config is None:
                raise ValueError("First call to KilnDisplay requires a config.")
            cls._instance = cls(config)
        return cls._instance

    def clear(self):
        """Fill the entire screen with black."""
        if not self.device:
            return
        with canvas(self.device) as draw:
            draw.rectangle((0, 0, self.width, self.height), outline="black", fill="black")

    def draw_overview(self, kiln_data):
        """
        Minimal overview: current temp, target temp, kiln state.
        Expand as needed to show runtime, profile name, etc.
        """
        if not self.device:
            return

        temp = kiln_data.get('temperature', 0.0)
        target = kiln_data.get('target', 0.0)
        state = kiln_data.get('state', 'IDLE')
        profile = kiln_data.get('profile', 'N/A')
        runtime = int(kiln_data.get('runtime', 0))

        with canvas(self.device) as draw:
            draw.text((2, 2), f"Now: {temp:.1f}C", font=self.font_large, fill="white")
            draw.text((2, 24), f"Set: {target:.1f}C", font=self.font_large, fill="white")
            draw.text((2, 46), f"State: {state}", font=self.font_small, fill="white")
            draw.text((2, 60), f"Profile: {profile}", font=self.font_small, fill="white")
            draw.text((2, 74), f"Runtime: {runtime}s", font=self.font_small, fill="white")

    def draw_diagram(self, kiln_data):
        """
        Simple placeholder for a 'graph' or 'diagram' screen.
        You could add a small line chart or bar chart here with PIL.
        """
        if not self.device:
            return

        # Example of drawing text or shapes
        with canvas(self.device) as draw:
            draw.text((10, 10), "Profile Diagram", font=self.font_small, fill="white")
            # ... you can plot (time vs. temperature) or (profile) here

    def draw_confirm_stop(self):
        """
        Confirmation screen: "Stop the kiln?" with a prompt
        """
        if not self.device:
            return
        with canvas(self.device) as draw:
            draw.text((20, 20), "STOP the Kiln?", font=self.font_large, fill="white")
            draw.text((20, 50), "Press to confirm", font=self.font_small, fill="white")

    def draw_start_burn(self):
        """
        Confirmation screen: "Start burn?"
        """
        if not self.device:
            return
        with canvas(self.device) as draw:
            draw.text((20, 20), "START Burn?", font=self.font_large, fill="white")
            draw.text((20, 50), "Press to confirm", font=self.font_small, fill="white")
