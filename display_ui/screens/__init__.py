# __init__.py in display_ui/screens/
from .overview_screen import OverviewScreen
from .manual_control_screen import ManualControlScreen
from .confirm_screen import ConfirmScreen
from .diagram_screen import DiagramScreen
from .profile_selector_screen import ProfileSelectorScreen
from .profile_builder_screen import ProfileBuilderScreen
from .settings_screen import SettingsScreen

def build_screens(display, ui):
    return {
        "overview": OverviewScreen(display, ui),
        "manual_control": ManualControlScreen(ui),
        "confirm": ConfirmScreen(ui),
        "diagram": DiagramScreen(ui),
        "profile_selector": ProfileSelectorScreen(ui),
        "profile_builder": ProfileBuilderScreen(ui),
        "settings": SettingsScreen(ui),
    }
