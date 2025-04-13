#!/usr/bin/env python3
# test_menu_ui.py - Simplified Version (NOW INSIDE display_ui)

import time
import random
import logging
import os
import sys

# --- Setup Logger Globally ---
# (Logger setup remains the same)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("test_menu_ui_simple")
# ----------------------------

# --- Ensure Project Root is in sys.path ---
# script_dir is now /path/to/project/display_ui
script_dir = os.path.dirname(os.path.abspath(__file__))
# project_root needs to be one level up from script_dir
project_root = os.path.abspath(os.path.join(script_dir, '..')) # <-- MODIFIED
if project_root not in sys.path:
    logger.info(f"Adding project root to sys.path: {project_root}")
    sys.path.insert(0, project_root)

# Add lib path relative to project root
lib_path = os.path.join(project_root, 'lib')
if lib_path not in sys.path:
     logger.info(f"Adding lib path to sys.path: {lib_path}")
     sys.path.insert(1, lib_path)
# ------------------------------------------

# --- Import Configuration ---
try:
    # Use relative import to go up one level from display_ui to project root
    from .. import config # <-- MODIFIED
    log_level_to_use = getattr(config, 'log_level', logging.INFO)
    logging.getLogger().setLevel(log_level_to_use)
    logger.info(f"Applied log level from config: {log_level_to_use}")
except ImportError:
     logger.error("Could not relatively import config from parent directory.")
     sys.exit(1)
except ModuleNotFoundError:
    logger.error("config.py not found in project root. Please ensure it exists.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Error importing or processing config.py: {e}", exc_info=True)
    sys.exit(1)
# -------------------------

# --- Import Core UI, Display, and Input Components ---
try:
    # Use relative imports for modules within display_ui package
    from .display_screen import KilnDisplay # <-- MODIFIED (relative)
    from .menu_ui import MenuUI # <-- MODIFIED (relative)
    from .rotary_input import RotaryInput # <-- MODIFIED (relative)
    from . import screens # <-- MODIFIED (relative import of the screens package)
except ImportError as e:
     logger.error(f"Failed to import UI/Display/Input modules: {e}", exc_info=True)
     sys.exit(1)
# --------------------------------------------------

# --- Conditional Hardware Import ---
# (This logic remains the same, checking config.enable_rotary_input)
rotary_available = False
GPIO = None # Define placeholder

if config.enable_rotary_input:
    logger.info("Rotary input enabled in config, attempting hardware library import...")
    try:
        import RPi.GPIO as GPIO # This global import is fine here
        # RotaryInput class itself handles internal GPIO usage now
        rotary_available = True
        logger.info("Successfully imported RPi.GPIO.")
    except (ImportError, ModuleNotFoundError, RuntimeError, Exception) as e:
        logger.warning(f"Failed to load RPi.GPIO ({type(e).__name__}: {e}). Physical rotary input disabled for this test.")
        rotary_available = False
else:
    logger.info("Rotary input is disabled in config.py.")
# -----------------------------------


# --- Main Test Function ---
def main():
    logger.info("--- Starting Simple UI Test (inside display_ui) ---")

    # --- Create Profile Directory ---
    # Path calculation uses the adjusted project_root
    profile_dir = os.path.join(project_root, "storage", "profiles") # <-- Path uses adjusted project_root
    if not os.path.isdir(profile_dir):
        logger.warning(f"Profile directory '{profile_dir}' not found. Creating it.")
        # ... (directory creation logic remains the same) ...
        storage_dir = os.path.join(project_root, "storage")
        if not os.path.isdir(storage_dir):
             try: os.makedirs(storage_dir)
             except OSError: pass
        if not os.path.isdir(profile_dir):
             try: os.makedirs(profile_dir)
             except OSError: logger.error(f"Failed to create profile directory: {profile_dir}")


    # --- Initialize Display ---
    try:
        display_config = getattr(config, 'DISPLAY_CONFIG', {}) # Get config safely
        display = KilnDisplay.get_instance(display_config)
        if display is None or not display.device:
             raise RuntimeError("KilnDisplay device initialization failed.")
        logger.info("Display initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize KilnDisplay: {e}", exc_info=True)
        sys.exit(1)

    # --- Initialize UI Manager ---
    try:
        ui = MenuUI(display)
        logger.info("MenuUI initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize MenuUI: {e}", exc_info=True)
        sys.exit(1)

    # --- Initialize and Start Rotary Input Thread ---
    rotary_thread = None
    if config.enable_rotary_input and rotary_available: # Check both config and library availability
        logger.info("Initializing and starting RotaryInput thread...")
        try:
            rotary_thread = RotaryInput(ui) # RotaryInput handles internal checks
            rotary_thread.start()
            if not rotary_thread.available:
                 logger.warning("RotaryInput thread started but hardware check failed.")
            else:
                 logger.info("RotaryInput thread started successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize or start RotaryInput thread: {e}", exc_info=True)
    # ... (Logging about rotary state remains the same) ...

    # --- Basic Static Data for Display ---
    static_kiln_data = {
            "temperature": 24.8, "target": 0.0, "state": "IDLE",
            "runtime": 0, "profile": getattr(config, 'last_selected_profile', 'TestProf'),
        }
    try:
        ui.send(static_kiln_data)
        logger.info(f"Sent initial static data to UI: {static_kiln_data}")
    except Exception as e: logger.error(f"Error sending initial data: {e}")

    # --- Main Loop ---
    logger.info("Starting test loop. UI is active.")
    if rotary_thread and rotary_thread.available: # Check if thread is running and available
        logger.info(">>> Use the physical rotary encoder to navigate. <<<")
    else: logger.info(">>> Physical rotary input unavailable/disabled. Cannot test navigation. <<<")
    logger.info("Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt: logger.info("Ctrl+C detected. Exiting test loop.")
    except Exception as e: logger.exception("An unexpected error occurred during the main test loop.")
    finally:
        # --- Cleanup ---
        logger.info("Performing cleanup...")
        if display:
            try: display.clear(); display.show(); logger.info("Display cleared.")
            except Exception as e: logger.error(f"Error during display cleanup: {e}")

        # Global GPIO Cleanup (check if GPIO module was loaded)
        if 'RPi.GPIO' in sys.modules:
             gpio_module = sys.modules['RPi.GPIO']
             if hasattr(gpio_module, 'cleanup'):
                  try: logger.info("Performing global GPIO cleanup..."); gpio_module.cleanup(); logger.info("Global GPIO cleanup done.")
                  except Exception as e: logger.error(f"Error during global GPIO cleanup: {e}")
             else: logger.warning("RPi.GPIO module loaded but no cleanup method found.")
        else: logger.info("RPi.GPIO module not loaded, skipping GPIO cleanup.")
        logger.info("Cleanup finished.")
        # --- End Cleanup ---

# --- Script Entry Point ---
if __name__ == "__main__":
    main()
# --------------------------