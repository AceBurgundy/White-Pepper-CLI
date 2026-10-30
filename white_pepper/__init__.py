"""
white-pepper: Centralized High-Fidelity Scanner and Computer Vision Suite.

This package provides hardware acquisition abstractions, computer vision algorithms,
typed configuration contracts, and document compilation utilities for desktop
and headless scanning workflows.
"""

from __future__ import annotations

# DPI = Dots Per Inch
# PDF = Portable Document Format
# MPL = Mozilla Public License

from white_pepper.config import (
    SUPPORTED_BACKEND_MODES,
    SUPPORTED_CARD_BACKGROUNDS,
    SUPPORTED_COLOR_MODES,
    SUPPORTED_DPI_VALUES,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_PDF_FIT_MODES,
    SUPPORTED_ROTATION_ANGLES,
    SUPPORTED_SCAN_INTENTS,
    BookletProcessConfiguration,
    CardProcessConfiguration,
    PdfCompilationConfiguration,
    ScanConfiguration,
)

__version__: str = "1.1.1"
__author__: str = "AceBurgundy"
__license__: str = "MPL-2.0"

__all__: list[str] = [
    "__version__",
    "__author__",
    "__license__",
    "SUPPORTED_DPI_VALUES",
    "SUPPORTED_COLOR_MODES",
    "SUPPORTED_SCAN_INTENTS",
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_BACKEND_MODES",
    "SUPPORTED_ROTATION_ANGLES",
    "SUPPORTED_PDF_FIT_MODES",
    "SUPPORTED_CARD_BACKGROUNDS",
    "ScanConfiguration",
    "CardProcessConfiguration",
    "BookletProcessConfiguration",
    "PdfCompilationConfiguration",
]
