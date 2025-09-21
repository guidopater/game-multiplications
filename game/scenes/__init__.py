"""Scene definitions for the multiplication game."""

from .main_menu import MainMenuScene
from .test_setup import TestSetupScene
from .test_session import TestSessionScene
from .test_summary import TestSummaryScene
from .practice_setup import PracticeSetupScene
from .practice_session import PracticeSessionScene
from .practice_summary import PracticeSummaryScene
from .progress_overview import ProgressOverviewScene
from .settings_scene import SettingsScene
from .profile_onboarding import ProfileOnboardingScene

__all__ = [
    "MainMenuScene",
    "TestSetupScene",
    "TestSessionScene",
    "TestSummaryScene",
    "PracticeSetupScene",
    "PracticeSessionScene",
    "PracticeSummaryScene",
    "ProgressOverviewScene",
    "SettingsScene",
    "ProfileOnboardingScene",
]
