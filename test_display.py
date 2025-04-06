import unittest
import time
import logging
from display_screen import KilnDisplay

# This configuration assumes you have:
#  1) Enabled hardware SPI in raspi-config.
#  2) Wired your display's CS pin to CE1 (GPIO7), and
#  3) Wired DC to GPIO13, RST to GPIO19, plus SCLK on GPIO11, MOSI on GPIO10.
# Note that Luma will automatically use the Pi’s hardware MOSI/SCLK lines (GPIO10/11)
# when you specify port=0, device=1.
#
# Make sure you match this to your actual physical wiring.

dummy_config = {
    # Telling our display code to use hardware SPI bus 0, chip select = CE1
    'port': 0,
    'device': 1,

    # Indicate which GPIO pins for DC and RST (these must match your wiring)
    'gpio_DC': 13,
    'gpio_RST': 19,

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

# Set test delay (in seconds) to slow down tests if you want to see what's on the screen
TEST_DELAY = 2

# Configure logging for test output
logging.basicConfig(level=logging.DEBUG)


class TestKilnDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize the singleton display once for all tests
        cls.display = KilnDisplay.get_instance(dummy_config)
    
    def tearDown(self):
        # Delay after each test so you can visually confirm the result on the display
        time.sleep(TEST_DELAY)
    
    def test_01_get_local_ip(self):
        """Test that get_local_ip() returns a non-empty string."""
        ip = self.display.get_local_ip()
        logging.info(f"Local IP from display: {ip}")
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)

    def test_02_update_method(self):
        """
        Test that the update() method runs without exceptions.
        We'll just pass some dummy data to see if anything is drawn.
        """
        try:
            # Simulate some kiln data
            current_temp = 123.4
            target_temp = 150
            kiln_state = "TESTING"
            
            self.display.update(current_temp, target_temp, kiln_state)
        except Exception as e:
            self.fail(f"display.update() raised an exception: {e}")

    def test_03_clear_method(self):
        """Test that clear() runs without exceptions (screen should turn blank)."""
        try:
            self.display.clear()
        except Exception as e:
            self.fail(f"display.clear() raised an exception: {e}")

    def test_04_send_method_with_dict(self):
        """
        Test the observer-like send() method with a dictionary.
        This should call update() internally.
        """
        data = {
            'ispoint': 200.0,
            'setpoint': 300.0,
            'state': 'RUNNING'
        }
        try:
            self.display.send(data)
        except Exception as e:
            self.fail(f"display.send() raised an exception: {e}")

    def test_05_send_method_with_string(self):
        """
        Test that sending a string does NOT crash
        (the display code should ignore non-dict messages).
        """
        try:
            self.display.send("This is not a dictionary")
        except Exception as e:
            self.fail(f"display.send() raised an exception with a string: {e}")


if __name__ == '__main__':
    unittest.main()
