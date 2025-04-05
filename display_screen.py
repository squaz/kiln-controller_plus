import time
import socket
import logging
from luma.core.interface.serial import spi  # Using generic SPI for hardware SPI
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import ImageFont, ImageDraw

logger = logging.getLogger(__name__)

class KilnDisplay:
    """
    Singleton class for managing the ST7735 display.
    
    This class initializes the display using the settings provided in a configuration
    dictionary (DISPLAY_CONFIG). Since the display is a unique hardware resource, the
    singleton pattern ensures only one instance is created and used across the entire
    application. This design keeps the display API simple and makes the system easier to
    test by allowing dependency injection (for example, substituting a mock display during testing).
    
    To use the display, always call:
        display = KilnDisplay.get_instance(config)
    """
    
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super(KilnDisplay, cls).__new__(cls)
        return cls._instance

    def __init__(self, config):
        # Prevent reinitialization of the singleton
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self.width = config.get('width', 160)
        self.height = config.get('height', 128)
        self.font_small = ImageFont.load_default()
        self.font_large = self.font_small

        try:
            # Retrieve hardware SPI pin assignments from the provided config
            spi_mosi = config['MOSI']
            spi_sclk = config['SCLK']
            pin_dc   = config['DC']
            pin_rst  = config['RST']
            spi_cs   = config['CS']

            logger.info(f"Initializing SPI with pins: MOSI={spi_mosi}, SCLK={spi_sclk}, DC={pin_dc}, RST={pin_rst}, CS={spi_cs}")
            self.spi = spi(
                gpio_MOSI=spi_mosi,
                gpio_SCLK=spi_sclk,
                gpio_DC=pin_dc,
                gpio_RST=pin_rst,
                gpio_CS=spi_cs,
                cs_high=True  # Some displays require CS to be held high
            )

            # Initialize the ST7735 device using the configuration settings
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

            # Load fonts as specified in the config
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

    @classmethod
    def get_instance(cls, config=None):
        """
        Returns the singleton instance of KilnDisplay.
        If the instance does not exist, a configuration must be provided to initialize it.
        """
        if cls._instance is None:
            if config is None:
                raise ValueError("Configuration must be provided for first initialization of KilnDisplay.")
            cls._instance = cls(config)
        return cls._instance

    def _wrap_line(self, text, font, max_width):
        """
        Wraps a single line of text so that it fits within max_width using the provided font.
        Returns a list of wrapped lines.
        """
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip() if current_line else word
            # Calculate text width using getbbox instead of getsize
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def display_message(self, lines, font=None):
        """
        Displays a list of text lines on the display with automatic word wrapping.
        
        :param lines: List (or array) of strings to display.
        :param font: Optional font to use; defaults to the small font.
        
        If a line is too long to fit on the display, it is wrapped into multiple lines.
        """
        if not self.device:
            return
        if font is None:
            font = self.font_small

        try:
            with canvas(self.device) as draw:
                padding = 2
                # Use getbbox to determine line height
                line_height = font.getbbox("A")[3]
                max_width = self.width - (padding * 2)
                final_lines = []
                # Wrap each line if necessary
                for text_line in lines:
                    wrapped = self._wrap_line(text_line, font, max_width)
                    final_lines.extend(wrapped)
                
                current_y = padding
                for line in final_lines:
                    if current_y + line_height > self.height:
                        break  # Stop if there's no more vertical space
                    draw.text((padding, current_y), line, fill="white", font=font)
                    current_y += line_height + 2  # spacing between lines
            logger.debug("Displayed message with wrapped text.")
        except Exception as e:
            logger.error(f"Error displaying message: {e}")

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
        """
        Attempts to determine the local IP address.
        """
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
        """
        Clears the display by filling it with black.
        """
        if self.device:
            try:
                with canvas(self.device) as draw:
                    draw.rectangle(self.device.bounding_box, outline="black", fill="black")
                logger.debug("Display cleared.")
            except Exception as e:
                logger.error(f"Error clearing display: {e}")
