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

        # Example: config.ROTARY_CONFIG = { 'clk': 21, 'dat': 20, 'btn': 16, 'invert_btn': False }
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

    def run(self):
        logger.info("[RotaryInput] Starting rotary poll loop...")
        while True:
            # Check rotation
            clk_val = GPIO.input(self.clk_pin)
            dat_val = GPIO.input(self.dat_pin)
            if clk_val != self.last_clk:
                # The encoder has moved
                if dat_val != clk_val:
                    self.ui.handle_rotary_event("rot_right")
                else:
                    self.ui.handle_rotary_event("rot_left")
                self.last_clk = clk_val

            # Check button
            btn_val = GPIO.input(self.btn_pin)
            btn_pressed = (btn_val == 0) if not self.invert_btn else (btn_val == 1)

            # If you only want to detect "press" on transitions:
            if btn_pressed and (self.last_btn != btn_val):
                self.ui.handle_rotary_event("press")

            self.last_btn = btn_val

            time.sleep(0.01)
