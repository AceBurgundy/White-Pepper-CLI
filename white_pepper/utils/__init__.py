"""
Terminal utilities, audio notifications, and interaction helpers.
"""

from __future__ import annotations

from white_pepper.utils.audio import (
    play_alert_beep,
    play_completion_beep,
    play_countdown_tick,
)
from white_pepper.utils.console import (
    display_countdown,
    is_current_window_focused,
    wait_for_spacebar,
)

__all__: list[str] = [
    "play_alert_beep",
    "play_completion_beep",
    "play_countdown_tick",
    "display_countdown",
    "is_current_window_focused",
    "wait_for_spacebar",
]
