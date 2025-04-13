#!/usr/bin/env python3
# test_menu_ui.py - Simplified for UI testing

import time
import logging
import os
import sys

# --- Setup Logger Globally ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("test_menu_ui_simple")
# ----------------------------

# --- Ensure Project Root is in sys.path ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(script_dir)
if project_root not in sys.path:
    logger.info(f"Adding project root to sys.path: {project_root}")
    sys.path.insert(0, project_root)

lib_path = os.path.join(project_root, 'lib')
if lib_path not in sys.path:
     logger.info(f"Adding lib path to sys.path: {lib_path}")
     sys.path.insert(1, lib_path)
# ------------------------------------------

# --- Import Configuration ---
try:
    import config
    # Override log level from config if specified
    log_level_to_use = getattr(config, 'log_level', logging.INFO)
    logging.getLogger().setLevel(log_level_to_use) # Apply level to root logger
    logger.info(f"Applied log level from config: {log_level_to_use}")
except ModuleNotFoundError:
    logger.error("config.py not found in project root. Please ensure it exists.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error importing or processing config.py: {e}", exc_info=True)
    sys.exit(1)
# -------------------------

# --- Import Core UI, Display, and Input Components ---
try:
    from display_screen import KilnDisplay
    from display_ui.menu_ui import MenuUI
    from display_ui.rotary_input import RotaryInput # Import RotaryInput directly
    import display_ui.screens # This registers the screens
except ImportError as e:
     logger.error(f"Failed to import UI/Display/Input modules: {e}", exc_info=True)
     sys.exit(1)
# --------------------------------------------------


# --- Main Test Function ---
def main():
    logger.info("--- Starting Simple UI Test ---")

    # --- Initialize Display ---
    try:
        display = KilnDisplay.get_instance(config.DISPLAY_CONFIG)
        if display is None or not display.device:
             raise RuntimeError("KilnDisplay instance created, but device initialization failed.")
        logger.info("Display initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize KilnDisplay: {e}", exc_info=True)
        sys.exit(1)
    # -------------------------

    # --- Initialize UI Manager ---
    try:
        ui = MenuUI(display)
        logger.info("MenuUI initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize MenuUI: {e}", exc_info=True)
        sys.exit(1)
    # --------------------------

    # --- Initialize and Start Rotary Input Thread (if enabled) ---
    rotary_thread = None
    if config.enable_rotary_input:
        logger.info("Rotary input enabled in config, initializing RotaryInput...")
        try:
            # Instantiate the class - it handles its own GPIO check internally
            rotary_thread = RotaryInput(ui)
            # Start the thread - it will run if GPIO was available, or exit otherwise
            rotary_thread.start()
            # Note: We don't need 'rotary_available' flag here anymore
            logger.info("RotaryInput thread started (will run if hardware is available).")
        except Exception as e:
            # Catch errors during instantiation or starting
            logger.error(f"Failed to initialize or start RotaryInput thread: {e}", exc_info=True)
    else:
        logger.info("Rotary input is disabled in config.py, thread not started.")
    # -------------------------------------------------------------

    # --- Basic Static Data for Display ---
    static_kiln_data = {
            "temperature": 28.1,
            "target": 0.0,
            "state": "IDLE",
            "runtime": 0,
            "profile": getattr(config, 'last_selected_profile', None) or "SimProf", # Use config or default
        }
    try:
        ui.send(static_kiln_data) # Send initial data once
        logger.info(f"Sent initial static data to UI: {static_kiln_data}")
    except Exception as e:
        logger.error(f"Error sending initial data to UI: {e}")
    # ------------------------------------

    # --- Main Loop ---
    logger.info("Starting test loop. UI is active.")
    if config.enable_rotary_input:
        logger.info(">>> If RotaryInput initialized successfully, use the physical encoder to navigate. <<<")
    else:
        logger.info(">>> Rotary input disabled in config. Cannot test navigation. <<<")
    logger.info("Press Ctrl+C to exit.")

    try:
        while True:
            # Keep the script alive. Interaction happens via the RotaryInput thread (if running)
            # sending events to the MenuUI instance.
            time.sleep(5) # Can sleep longer as no dynamic updates are sent from here

    except KeyboardInterrupt:
        logger.info("Ctrl+C detected. Exiting test loop.")
    except Exception as e:
         logger.exception("An unexpected error occurred during the main test loop.")
    finally:
        # --- Cleanup ---
        logger.info("Performing cleanup...")
        # Optional: Signal rotary thread to stop if needed (though daemon should exit)
        # if rotary_thread and hasattr(rotary_thread, 'stop'):
        #    rotary_thread.stop()

        if display:
            try:
                display.clear()
                display.show()
                logger.info("Display cleared.")
            except Exception as e:
                logger.error(f"Error during display cleanup: {e}")

        # --- Global GPIO Cleanup ---
        # It's often best practice to do cleanup once when the main app exits
        # Check if the GPIO object was successfully imported by RotaryInput
        gpio_module = sys.modules.get('RPi.GPIO') # Check if module is loaded
        if gpio_module and hasattr(gpio_module, 'cleanup'):
             try:
                  logger.info("Performing global GPIO cleanup...")
                  gpio_module.cleanup()
                  logger.info("Global GPIO cleanup done.")
             except Exception as e:
                  logger.error(f"Error during global GPIO cleanup: {e}")
        else:
             logger.info("RPi.GPIO module not loaded or no cleanup needed.")
        # --- End Global GPIO Cleanup ---

        logger.info("Cleanup finished.")
        # --- End Cleanup ---

# --- Script Entry Point ---
if __name__ == "__main__":
    main()
# --------------------------