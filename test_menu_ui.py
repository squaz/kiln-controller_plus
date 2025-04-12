#!/usr/bin/env python3

import time
import random
import logging

# Import your real config.py
import config

# Import the classes from your new files
from display_screen import KilnDisplay
from menu_ui import MenuUI
from rotary_input import RotaryInput

def main():
    logging.basicConfig(level=config.log_level, format=config.log_format)
    log = logging.getLogger("test_menu_ui")

    # 1) Initialize the KilnDisplay with config.DISPLAY_CONFIG
    display = KilnDisplay.get_instance(config.DISPLAY_CONFIG)

    # 2) Create the MenuUI
    ui = MenuUI(display)

    # 3) Optionally start the rotary polling thread if enabled in config
    if config.enable_rotary_input:
        log.info("Rotary input is enabled. Starting rotary thread...")
        rotary_thread = RotaryInput(ui)  # reads pins from config.ROTARY_CONFIG
        rotary_thread.start()
    else:
        log.info("Rotary input is disabled in config.py.")

    log.info("Starting fake data loop. Rotate/press the knob (if enabled) to test UI states.")

    start_time = time.time()
    try:
        while True:
            # Generate some random or semi-random data to simulate kiln
            temperature = 25.0 + random.uniform(-2, 2)  # e.g. ~25 +/- 2
            target = 30.0
            runtime = int(time.time() - start_time)

            # Build a fake data dict
            data = {
                "temperature": temperature,
                "target": target,
                "state": "TESTING",
                "runtime": runtime,
                "profile": "FAKE_PROFILE",
            }

            # Send it to the MenuUI's observer interface
            ui.send(data)

            # Wait a bit, then loop
            time.sleep(2.0)

    except KeyboardInterrupt:
        log.info("Exiting test.")

if __name__ == "__main__":
    main()
