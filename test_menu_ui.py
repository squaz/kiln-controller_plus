#!/usr/bin/env python3

import time
import random
import logging

# Real config
import config

# Updated import paths
from display_screen import KilnDisplay
from display_ui.menu_ui import MenuUI
from display_ui.rotary_input import RotaryInput

# This will run the screen registration logic
import display_ui.screens

def main():
    logging.basicConfig(level=config.log_level, format=config.log_format)
    log = logging.getLogger("test_menu_ui")

    # Initialize the display
    display = KilnDisplay.get_instance(config.DISPLAY_CONFIG)

    # Set up the MenuUI
    ui = MenuUI(display)

    # Start rotary input if enabled
    if config.enable_rotary_input:
        log.info("Rotary input is enabled. Starting rotary thread...")
        rotary_thread = RotaryInput(ui)
        rotary_thread.start()
    else:
        log.info("Rotary input is disabled in config.py.")

    log.info("Starting test loop. You can rotate or press the encoder to test the menu.")

    start_time = time.time()
    try:
        while True:
            # Simulate kiln data
            temperature = 25.0 + random.uniform(-2, 2)
            target = 30.0
            runtime = int(time.time() - start_time)

            data = {
                "temperature": temperature,
                "target": target,
                "state": "TESTING",
                "runtime": runtime,
                "profile": "FAKE_PROFILE",
            }

            # Send the data to the UI
            ui.send(data)

            time.sleep(2.0)

    except KeyboardInterrupt:
        log.info("Exiting test.")

if __name__ == "__main__":
    main()
