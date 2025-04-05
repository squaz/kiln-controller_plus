import unittest
import time
import logging
from display_screen import KilnDisplay

# Dummy configuration for testing (matches your production settings)
dummy_config = {
    'MOSI': 10,    # SDA
    'SCLK': 11,    # SCLK
    'DC': 13,      # RS (Data/Command)
    'RST': 19,     # RES (Reset)
    'CS': 26,      # CS
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

# Set test delay (in seconds) to slow down tests if needed
TEST_DELAY = 2

# Configure logging for test output
logging.basicConfig(level=logging.DEBUG)

class TestKilnDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize the singleton display instance once for all tests
        cls.display = KilnDisplay.get_instance(dummy_config)
    
    def tearDown(self):
        # Delay after each test to allow for visual confirmation or hardware settling
        time.sleep(TEST_DELAY)
    
    def test_get_local_ip(self):
        """Test that get_local_ip returns a non-empty string."""
        ip = self.display.get_local_ip()
        logging.info(f"Local IP: {ip}")
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) > 0)

    def test_update_method(self):
        """Test that the update method runs without exceptions."""
        ip = self.display.get_local_ip()
        try:
            self.display.update(ip, current_temp=123.4, target_temp=150,
                                current_step=2, remaining_step_time="3m",
                                remaining_total_time="15m")
        except Exception as e:
            self.fail(f"update() method raised an exception: {e}")

    def test_display_message_wrapping(self):
        """Test display_message with multiple lines that require wrapping."""
        test_lines = [
            "This is a very long test message that should automatically wrap into multiple lines on the display.",
            "Second line for testing.",
            "Third line is also intentionally long to verify the wrapping logic works as expected."
        ]
        try:
            self.display.display_message(test_lines)
        except Exception as e:
            self.fail(f"display_message() method raised an exception: {e}")
    
    def test_clear_method(self):
        """Test that clear() runs without exceptions."""
        try:
            self.display.clear()
        except Exception as e:
            self.fail(f"clear() method raised an exception: {e}")

if __name__ == '__main__':
    unittest.main()
