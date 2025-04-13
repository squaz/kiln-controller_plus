# --- START OF FILE: display_ui/rotary_input.py ---
import threading
import time
import logging
import config

GPIO = None # Placeholder

logger = logging.getLogger(__name__)

class RotaryInput(threading.Thread):
    # ... (__init__ remains the same) ...
    def __init__(self, ui_manager):
        super().__init__(daemon=True)
        self.ui = ui_manager
        self.available = False # Assume unavailable until proven otherwise
        self.clk_pin = None
        self.dat_pin = None
        self.btn_pin = None
        self.invert_btn = False
        self.last_clk = None
        self.btn_down_time = None
        self.press_threshold = 0.8
        self.debounce_delay = 0.05
        self.polling_interval = 0.005 # Short interval for responsiveness
        self._stop_event = threading.Event() # Added for cleaner thread stop

        logger.info("[RotaryInput] Initializing...")
        try:
            global GPIO
            import RPi.GPIO as GPIO_imported
            GPIO = GPIO_imported
            logger.info("[RotaryInput] RPi.GPIO imported successfully.")
            cfg = config.ROTARY_CONFIG
            self.clk_pin = cfg.get('clk')
            self.dat_pin = cfg.get('dat')
            self.btn_pin = cfg.get('btn')
            self.invert_btn = cfg.get('invert_btn', False)
            if None in [self.clk_pin, self.dat_pin, self.btn_pin]:
                 raise ValueError("Rotary pin configuration missing (clk, dat, or btn)")
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.dat_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(f"[RotaryInput] GPIO pins configured: CLK={self.clk_pin}, DT={self.dat_pin}, SW={self.btn_pin}")
            self.last_clk = GPIO.input(self.clk_pin)
            self.available = True
            logger.info("[RotaryInput] Initialization successful, hardware input available.")
        except Exception as e:
            logger.warning(f"[RotaryInput] Initialization failed ({type(e).__name__}: {e}). Hardware input disabled.")
            self.available = False

    def run(self):
        if not self.available:
            logger.warning("[RotaryInput] Thread exiting, hardware not available.")
            return

        logger.info("[RotaryInput] Starting rotary poll loop...")
        while not self._stop_event.is_set(): # Check stop event
            try:
                # --- Rotation Check ---
                clk_val = GPIO.input(self.clk_pin) # Read CLK pin
                if clk_val != self.last_clk:
                    time.sleep(0.002) # Debounce rotation slightly
                    dat_val = GPIO.input(self.dat_pin) # Read DAT pin
                    if dat_val != clk_val:
                        self.ui.handle_rotary_event("rot_right")
                    else:
                        self.ui.handle_rotary_event("rot_left")
                self.last_clk = clk_val # Update last CLK state

                # --- Button Check ---
                btn_val = GPIO.input(self.btn_pin) # Read BTN pin
                btn_state = (btn_val == 0) if not self.invert_btn else (btn_val == 1)
                now = time.time()

                if btn_state and not self.btn_down_time: # Button pressed
                    self.btn_down_time = now
                elif not btn_state and self.btn_down_time: # Button released
                    if (now - self.btn_down_time) > self.debounce_delay:
                        duration = now - self.btn_down_time
                        event = "long_press" if duration >= self.press_threshold else "short_press"
                        logger.debug(f"[RotaryInput] {event.replace('_',' ').title()} detected.")
                        self.ui.handle_rotary_event(event) # Send event to UI
                    self.btn_down_time = None # Reset timer

                time.sleep(self.polling_interval) # Main polling loop delay

            # --- Refined Exception Handling ---
            except AttributeError as ae:
                # Log the specific attribute error
                logger.error(f"[RotaryInput] AttributeError in polling loop: {ae}. Stopping thread.", exc_info=True)
                break # Exit loop on error
            except RuntimeError as re:
                 # Catch potential runtime errors from GPIO library itself
                 logger.error(f"[RotaryInput] RuntimeError in polling loop: {re}. Stopping thread.", exc_info=True)
                 break # Exit loop on error
            except Exception as e:
                 # Catch any other unexpected errors
                 logger.error(f"[RotaryInput] Unexpected error in polling loop: {e}", exc_info=True)
                 time.sleep(1) # Wait a bit before retrying after other errors
            # --- End Refined Handling ---

        logger.info("[RotaryInput] Polling loop stopped.")

    def stop(self):
        """Signals the run loop to stop."""
        logger.info("[RotaryInput] Stop requested.")
        self._stop_event.set()
        # Note: GPIO cleanup should happen globally by the main application

# --- END OF FILE: display_ui/rotary_input.py ---