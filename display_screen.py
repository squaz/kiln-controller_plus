from luma.core.interface.serial import spi
from luma.lcd.device import st7735
from luma.core.render import canvas
from PIL import ImageFont
import logging, socket
from lib.base_observer import BaseObserver

logger = logging.getLogger(__name__)

class KilnDisplay(BaseObserver):
    """
    KilnDisplay is a singleton that also acts as an observer for OvenWatcher.
    This version displays:
      - IP Address
      - Current vs. Target Temperature
      - Kiln State
      - Error from Target (from pidstats["err"])
      - Elapsed Runtime
      - Current Profile Name

    It uses the same naming as the web UI:
      - 'temperature'    -> current measured temp
      - 'target'         -> current target temp
      - 'state'          -> "RUNNING", "PAUSED", ...
      - 'runtime'        -> elapsed seconds
      - 'profile'        -> name of the loaded schedule
      - 'pidstats'       -> dictionary with keys: "err", "p", "i", "d", etc.
    """

    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config):
        # Prevent re-initializing if already done
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # Initialize BaseObserver manually
        BaseObserver.__init__(self, observer_type="display")

        self.width = config.get('width', 160)
        self.height = config.get('height', 128)

        # Load fonts; fallback to default if error
        self.font_small = ImageFont.load_default()
        self.font_large = self.font_small
        font_path = config.get('font_path', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        try:
            self.font_small = ImageFont.truetype(font_path, config.get('font_small_size', 11))
            self.font_large = ImageFont.truetype(font_path, config.get('font_large_size', 13))
        except Exception as e:
            logger.warning(f"[KilnDisplay] Could not load custom fonts: {e}")

        # Initialize hardware SPI. Assume port=0, device=1, or whatever your wiring is:
        try:
            serial = spi(
                port=0,
                device=1,
                gpio_DC=13,   # DC pin
                gpio_RST=19,  # Reset pin
                bus_speed_hz=4000000
            )

            self.device = st7735(
                serial,
                rotate=config.get('rotate', 0),
                width=self.width,
                height=self.height,
                bgr=config.get('bgr', False)
            )
            logger.info("[KilnDisplay] ST7735 display initialized (hardware SPI).")

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

    def send(self, data):
        """
        Called by OvenWatcher whenever it has new kiln data.

        We expect 'data' to be a dict that includes:
            data["temperature"] -> current measured temp
            data["target"]      -> current target temp
            data["state"]       -> "RUNNING", "PAUSED", ...
            data["runtime"]     -> total seconds since profile start
            data["profile"]     -> name of loaded schedule or None
            data["pidstats"]    -> dict with "err", "p", "i", etc.
        """
        if not self.device:
            return
        if not isinstance(data, dict):
            logger.debug(f"[KilnDisplay] Ignoring non-dict: {data}")
            return

        # Collect the relevant fields
        current_temp = data.get('temperature', 0.0)
        target_temp  = data.get('target', 0.0)
        kiln_state   = data.get('state', 'IDLE')
        runtime      = data.get('runtime', 0.0)  # seconds
        profile_name = data.get('profile', 'N/A')

        # For error, we read from pidstats:
        pidstats = data.get('pidstats', {})
        kiln_err = pidstats.get('err', 0.0)

        # Update the display
        self.update(current_temp, target_temp, kiln_state, kiln_err, runtime, profile_name)

    def update(self, current_temp, target_temp, kiln_state,
               kiln_err=0.0, runtime=0.0, profile_name='N/A'):
        """
        Draw text on the ST7735 screen.
        """
        if not self.device:
            return
        try:
            with canvas(self.device) as draw:
                # 1) IP address
                ip_str = f"IP: {self.get_local_ip()}"
                draw.text((2, 0), ip_str, fill="white", font=self.font_small)

                # 2) Current vs. Target
                temp_str = f"Now: {current_temp:.1f}C / Set: {target_temp:.1f}C"
                draw.text((2, 16), temp_str, fill="white", font=self.font_large)

                # 3) Kiln state
                state_str = f"State: {kiln_state}"
                draw.text((2, 40), state_str, fill="white", font=self.font_small)

                # 4) Error from target
                err_str = f"Err: {kiln_err:+.1f}C"
                draw.text((2, 56), err_str, fill="white", font=self.font_small)

                # 5) Elapsed runtime
                run_str = f"Runtime: {runtime:.0f}s"
                draw.text((2, 72), run_str, fill="white", font=self.font_small)

                # 6) Current profile name
                prof_str = f"Profile: {profile_name}"
                draw.text((2, 88), prof_str, fill="white", font=self.font_small)

        except Exception as e:
            logger.error(f"[KilnDisplay] Error drawing: {e}")

    @staticmethod
    def get_local_ip():
        """
        Attempt to get the local IP; return "No IP Found" on failure.
        """
        s = None
        ip = "No IP Found"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            pass
        finally:
            if s:
                s.close()
        return ip

    def clear(self):
        """
        Fill screen with black.
        """
        if not self.device:
            return
        try:
            with canvas(self.device) as draw:
                draw.rectangle((0, 0, self.width, self.height), outline="black", fill="black")
        except Exception as e:
            logger.error(f"[KilnDisplay] Error clearing: {e}")
