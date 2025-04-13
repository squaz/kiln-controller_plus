# rotary_input.py
import threading
import time
import logging
import RPi.GPIO as GPIO
import config

logger = logging.getLogger(__name__)

class RotaryInput(threading.Thread):
    """
    Polls a KY-040 rotary encoder. On each step or button press,
    calls ui_manager.handle_rotary_event(...)
    """
    def __init__(self, ui_manager):
        super().__init__(daemon=True)
        self.ui = ui_manager

        cfg = config.ROTARY_CONFIG
        self.clk_pin = cfg['clk']
        self.dat_pin = cfg['dat']
        self.btn_pin = cfg['btn']
        self.invert_btn = cfg.get('invert_btn', False)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dat_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.last_clk = GPIO.input(self.clk_pin)
        self.last_btn = GPIO.input(self.btn_pin)
        self.btn_down_time = None
        self.press_threshold = 0.8  # seconds for long press

    def run(self):
        logger.info("[RotaryInput] Starting rotary poll loop...")
        while True:
            # Check rotation
            clk_val = GPIO.input(self.clk_pin)
            dat_val = GPIO.input(self.dat_pin)
            if clk_val != self.last_clk:
                if dat_val != clk_val:
                    self.ui.handle_rotary_event("rot_right")
                else:
                    self.ui.handle_rotary_event("rot_left")
                self.last_clk = clk_val

            # Check button
            btn_val = GPIO.input(self.btn_pin)
            btn_pressed = (btn_val == 0) if not self.invert_btn else (btn_val == 1)

            now = time.time()

            if btn_pressed and not self.btn_down_time:
                self.btn_down_time = now  # button just pressed

            if not btn_pressed and self.btn_down_time:
                duration = now - self.btn_down_time
                self.btn_down_time = None

                if duration >= self.press_threshold:
                    self.ui.handle_rotary_event("long_press")
                else:
                    self.ui.handle_rotary_event("short_press")

            self.last_btn = btn_val
            time.sleep(0.01)
