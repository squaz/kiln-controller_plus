# __init__.py in display_ui/screens/
import logging
from .overview_screen import OverviewScreen
#from .manual_control_screen import ManualControlScreen
from .confirm_screen import ConfirmScreen
from .diagram_screen import DiagramScreen
from .profile_selector_screen import ProfileSelectorScreen
#from .profile_builder_screen import ProfileBuilderScreen
#from .settings_screen import SettingsScreen

# Note: Component screens (ScrollableList, ValueInputScreen) are NOT registered here.
# They are instantiated dynamically by the screens that use them.

logger = logging.getLogger(__name__)

def build_screens(display, ui_manager):
    """
    Instantiates and returns a dictionary of all primary navigable screens.
    These are the screens that can appear in the main tab bar or be switched to directly.
    """
    logger.info("Building primary UI screens...")
    screens = {
        "overview": OverviewScreen(ui_manager), # Pass only ui_manager
        #"manual_control": ManualControlScreen(ui_manager),
        "confirm": ConfirmScreen(ui_manager), # Keep confirm registered for easy access
        "diagram": DiagramScreen(ui_manager),
        "profile_selector": ProfileSelectorScreen(ui_manager),
        #"profile_builder": ProfileBuilderScreen(ui_manager),
        #"settings": SettingsScreen(ui_manager),
    }
    logger.info(f"Screens built: {list(screens.keys())}")
    return screens
