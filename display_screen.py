import logging
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import ImageFont

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
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()

        # Initialize SPI device
        try:
            serial = spi(
                port=0,
                device=1,
                gpio_DC=13,
                gpio_RST=19,
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

    def draw_lines(self, lines):
        """
        Draws a list of lines using font_small with spacing.
        """
        if not self.device:
            return
        with canvas(self.device) as draw:
            y = 0
            for line in lines:
                draw.text((2, y), line, font=self.font_small, fill="white")
                y += 14

    def draw_custom(self, draw_fn):
        """
        Give low-level drawing access to a screen via a callback:
        Example usage:
            display.draw_custom(lambda draw: draw.line(...))
        """
        if not self.device:
            return
        with canvas(self.device) as draw:
            draw_fn(draw)