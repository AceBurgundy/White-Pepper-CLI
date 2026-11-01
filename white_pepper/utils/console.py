"""
Interactive console utilities, countdown displays, and window focus tracking.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Optional

from white_pepper.utils.audio import play_countdown_tick


def is_current_window_focused() -> bool:
    """
    Check whether the current console window has active operating system focus.

    Parameters
    ----------
    None

    Returns
    -------
    bool
        True if the console window currently has focus, False otherwise.
    """
    if sys.platform != "win32":
        return True

    try:
        user32_library: object = ctypes.windll.user32
        kernel32_library: object = ctypes.windll.kernel32

        foreground_window_handle: int = int(user32_library.GetForegroundWindow())  # type: ignore[attr-defined]
        console_window_handle: int = int(kernel32_library.GetConsoleWindow())  # type: ignore[attr-defined]

        if console_window_handle == 0:
            return True

        has_focus: bool = foreground_window_handle == console_window_handle
        return has_focus
    except Exception:
        return True


def wait_for_spacebar(prompt_message: str = "Press SPACEBAR when ready (or Ctrl+C to stop)...") -> None:
    """
    Pause execution until the operator presses the spacebar in the active console.

    Parameters
    ----------
    prompt_message : str, optional
        Message displayed to prompt the user.

    Returns
    -------
    None
    """
    print(prompt_message)
    if sys.platform == "win32":
        try:
            import msvcrt

            while True:
                if msvcrt.kbhit():
                    key_code: bytes = msvcrt.getch()
                    if key_code == b" ":
                        return
                    if key_code == b"\x03":
                        raise KeyboardInterrupt()
                time.sleep(0.05)
        except ImportError:
            input("Press ENTER to proceed...")
    else:
        input("Press ENTER to proceed...")


def display_countdown(
    total_seconds: int,
    action_description: str = "Next scan starts in",
    enable_audio_tick: bool = False,
) -> None:
    """
    Display a responsive countdown timer on a single console line.

    Parameters
    ----------
    total_seconds : int
        The duration in seconds to count down.
    action_description : str, optional
        Description prefix for the timer display.
    enable_audio_tick : bool, optional
        Whether to play a tick tone on each second elapsed.

    Returns
    -------
    None
    """
    for remaining_seconds in range(total_seconds, 0, -1):
        formatted_message: str = (
            f"\r  [{action_description}] {remaining_seconds:2d}s (Ctrl + C to stop)... "
        )
        sys.stdout.write(formatted_message)
        sys.stdout.flush()
        if enable_audio_tick and remaining_seconds <= 3:
            play_countdown_tick()
        time.sleep(1.0)

    completion_line: str = (
        f"\r  [{action_description}] 0s — Starting operation!                         \n"
    )
    sys.stdout.write(completion_line)
    sys.stdout.flush()
