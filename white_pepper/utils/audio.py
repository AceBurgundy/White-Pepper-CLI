"""
Acoustic notifications and tone generation for hardware events.
"""

from __future__ import annotations

import sys


def play_completion_beep(frequency_hertz: int = 1200, duration_milliseconds: int = 150) -> None:
    """
    Play a pleasant success tone using system audio.

    Parameters
    ----------
    frequency_hertz : int, optional
        Frequency of the tone in Hertz (default is 1200).
    duration_milliseconds : int, optional
        Duration of the tone in milliseconds (default is 150).

    Returns
    -------
    None
    """
    if sys.platform == "win32":
        try:
            import winsound

            winsound.Beep(frequency_hertz, duration_milliseconds)
        except Exception:
            pass


def play_countdown_tick(frequency_hertz: int = 800, duration_milliseconds: int = 50) -> None:
    """
    Play a brief tick tone during interval countdowns.

    Parameters
    ----------
    frequency_hertz : int, optional
        Frequency of the tick in Hertz (default is 800).
    duration_milliseconds : int, optional
        Duration of the tick in milliseconds (default is 50).

    Returns
    -------
    None
    """
    if sys.platform == "win32":
        try:
            import winsound

            winsound.Beep(frequency_hertz, duration_milliseconds)
        except Exception:
            pass


def play_alert_beep(frequency_hertz: int = 500, duration_milliseconds: int = 400) -> None:
    """
    Play an alert or warning tone when attention is required.

    Parameters
    ----------
    frequency_hertz : int, optional
        Frequency of the alert tone in Hertz (default is 500).
    duration_milliseconds : int, optional
        Duration of the alert tone in milliseconds (default is 400).

    Returns
    -------
    None
    """
    if sys.platform == "win32":
        try:
            import winsound

            winsound.Beep(frequency_hertz, duration_milliseconds)
        except Exception:
            pass
