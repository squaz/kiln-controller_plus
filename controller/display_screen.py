import time
import socket
import logging
from luma.core.interface.serial import spi  # Using generic SPI for software SPI
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw

logger = logging.getLogger(__name__)

class KilnDisplay:
    """
    Manages an ST7735 display using software SPI for the Kiln Controller.
    Handles initialization, updates, clearing, and basic messaging.
    """
    def __init__(self, config):
        """
        Initialize the display using software SPI.
        :param config: Dictionary containing pin configuration (MOSI, SCLK, DC, RST, CS),
                       display settings (width, height, rotate, etc.), and
                       font settings (font_path, font_small_size, font_large_size).
        """
        self.device = None
        self.width = config.get('width', 160)
        self.height = config.get('height', 128)
        self.font_small = ImageFont.load_default()  # Default fallback
        self.font_large = self.font_small  # Default fallback

        try:
            # --- Software SPI Setup ---
            # New GPIO mapping:
            # SCLK: GPIO26, SDA (MOSI): GPIO19, RS (DC): GPIO6, RES (Reset): GPIO13, CS: GPIO5
            spi_mosi = config.get('MOSI',  10) #19)  # GPIO19
            spi_sclk = config.get('SCLK',  11) #26)  # GPIO26
            pin_dc   = config.get('DC', 6)     # GPIO6
            pin_rst  = config.get('RST', 13)    # GPIO13
            spi_cs   = config.get('CS', 5)      # GPIO5

            logger.info(f"Initializing Software SPI: MOSI={spi_mosi}, SCLK={spi_sclk}, DC={pin_dc}, RST={pin_rst}, CS={spi_cs}")
            self.spi = spi(
                gpio_MOSI=spi_mosi,
                gpio_SCLK=spi_sclk,
                gpio_DC=pin_dc,
                gpio_RST=pin_rst,
                gpio_CS=spi_cs,
                cs_high=True,  # Some displays require CS to be held high in software SPI mode
            )

            # --- ST7735 Device Initialization ---
            self.device = st7735(
                self.spi,
                rotate=config.get('rotate', 0),
                width=self.width,
                height=self.height,
                h_offset=config.get('h_offset', 0),
                v_offset=config.get('v_offset', 0),
                bgr=config.get('bgr', False)
            )
            logger.info(f"ST7735 display initialized successfully ({self.width}x{self.height}).")

            # --- Font Loading ---
            try:
                font_path = config.get('font_path', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
                small_size = config.get('font_small_size', 11)
                large_size = config.get('font_large_size', 16)
                self.font_small = ImageFont.truetype(font_path, small_size)
                self.font_large = ImageFont.truetype(font_path, large_size)
                logger.info(f"Loaded font '{font_path}' sizes {small_size} & {large_size}.")
            except IOError:
                logger.warning(f"Font file not found at {font_path}. Using default PIL font.")
            except Exception as e:
                logger.warning(f"Error loading font: {e}. Using default PIL font.")

        except ImportError as e:
            logger.error(f"ImportError: {e}. Is luma.lcd installed? Is SPI enabled?")
            self.device = None
        except FileNotFoundError as e:
            logger.error(f"GPIO Error: {e}. Ensure GPIO pins are valid and user has permissions (add to 'gpio' group?).")
            self.device = None
        except Exception as e:
            logger.error(f"Failed to initialize ST7735 display: {e}")
            self.device = None

    def update(self, ip, current_temp, target_temp, current_step, remaining_step_time, remaining_total_time):
        """
        Update the display with kiln status information.
        """
        if not self.device:
            return

        try:
            with canvas(self.device) as draw:
                draw.text((2, 0), f"IP: {ip}", fill="white", font=self.font_small)
                temp_text = f"Now: {current_temp:.1f} C"
                if target_temp is not None:
                    temp_text += f" / Set: {target_temp:.0f} C"
                draw.text((2, 14), temp_text, fill="white", font=self.font_large)
                draw.text((2, 36), f"Step: {current_step}", fill="white", font=self.font_small)
                draw.text((2, 50), f"Step Left: {remaining_step_time}", fill="white", font=self.font_small)
                draw.text((2, 64), f"Total Left: {remaining_total_time}", fill="white", font=self.font_small)
        except Exception as e:
            logger.error(f"Error during display update: {e}")

    @staticmethod
    def get_local_ip():
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                ip = "No IP Found"
        finally:
            if s:
                s.close()
        return ip

    def clear(self):
        """Clears the display (fills with black)."""
        if self.device:
            try:
                with canvas(self.device) as draw:
                    draw.rectangle(self.device.bounding_box, outline="black", fill="black")
                logger.debug("Display cleared.")
            except Exception as e:
                logger.error(f"Error clearing display: {e}")

    def display_message(self, line1, line2="", line3="", font=None):
        """
        Displays up to three lines of text with a black background and white text.
        """
        if not self.device:
            return
        if font is None:
            font = self.font_small

        try:
            with canvas(self.device) as draw:
                padding = 2
                line_height = font.getbbox("A")[3]
                draw.rectangle(self.device.bounding_box, outline="black", fill="black")
                draw.text((padding, padding), line1, fill="white", font=font)
                if line2:
                    draw.text((padding, padding + line_height + 2), line2, fill="white", font=font)
                if line3:
                    draw.text((padding, padding + 2 * (line_height + 2)), line3, fill="white", font=font)
            logger.debug(f"Displayed message: {line1} | {line2} | {line3}")
        except Exception as e:
            logger.error(f"Error displaying message: {e}")
