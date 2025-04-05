import time
import logging
import sys
# Ensure the 'controller' directory is in the Python path
sys.path.insert(0, './controller')
try:
    from display_screen import KilnDisplay
except ImportError as e:
    print(f"Error importing KilnDisplay: {e}")
    print("Make sure display_screen.py is in the 'controller' subdirectory relative to this script.")
    sys.exit(1)

# New GPIO mapping for software SPI:
# SCLK: GPIO26, SDA (MOSI): GPIO19, RS (DC): GPIO6, RES (Reset): GPIO13, CS: GPIO5
DISPLAY_CONFIG = {
    'MOSI': 10,    # SDA on GPIO19
    'SCLK': 11,    # SCLK on GPIO26
    'DC': 13,      # RS (DC) on GPIO6
    'RST': 19,    # RES (Reset) on GPIO13
    'CS': 26,      # CS on GPIO5
    'width': 160,
    'height': 128,
    'rotate': 0,
    'h_offset': 0,
    'v_offset': 0,
    'bgr': False,
    'font_path': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'font_small_size': 11,
    'font_large_size': 16,
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("TestDisplay")

if __name__ == "__main__":
    logger.info("Starting standalone display test...")

    # Initialize display
    display = KilnDisplay(DISPLAY_CONFIG)

    if display.device is None:
        logger.error("Display initialization failed. Check connections, config, and logs. Exiting.")
        sys.exit(1)

    try:
        logger.info("Display initialized. Running test sequence...")

        # 1. Show startup message
        ip = display.get_local_ip()
        display.display_message("Kiln Display Test", ip, "Starting...")
        time.sleep(3)

        # 2. Cycle through dummy data using update()
        for i in range(5):
            temp = 25.0 + (i * 55.5)
            target = 1000.0
            step_name = f"Ramp {i+1}"
            step_time_s = 1800 - (i * 300)
            total_time_s = 7200 - (i * 300)

            step_time_str = time.strftime('%H:%M:%S', time.gmtime(step_time_s))
            total_time_str = time.strftime('%H:%M:%S', time.gmtime(total_time_s))

            logger.info(f"Updating display: Temp={temp:.1f}, Step={step_name}")
            display.update(
                ip=ip,
                current_temp=temp,
                target_temp=target,
                current_step=step_name,
                remaining_step_time=step_time_str,
                remaining_total_time=total_time_str
            )
            time.sleep(2)

        # 3. Show final message
        logger.info("Test sequence complete. Showing final message.")
        display.display_message("Test Complete!", "", "Check console.", font=display.font_large)
        time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    except Exception as e:
        logger.error(f"An error occurred during the test: {e}")
    finally:
        logger.info("Cleaning up display...")
        if display and display.device:
            display.clear()
        logger.info("Standalone test finished.")
