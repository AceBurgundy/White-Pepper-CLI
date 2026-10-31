"""
Computer vision algorithms, mathematical transformations, and geometry models.
"""

from __future__ import annotations

from white_pepper.algorithms.booklet_vision import (
    BookletPageSegment,
    segment_booklet_spread,
)
from white_pepper.algorithms.card_vision import (
    CardExtractionResult,
    extract_and_deskew_id_card,
)
from white_pepper.algorithms.geometry import (
    ID1_CORNER_RADIUS_MILLIMETERS,
    ID1_HEIGHT_MILLIMETERS,
    ID1_WIDTH_MILLIMETERS,
    PAPER_SIZE_REGISTRY,
    PLATEN_MAX_HEIGHT_ESCL_UNITS,
    PLATEN_MAX_HEIGHT_INCHES,
    PLATEN_MAX_HEIGHT_MILLIMETERS,
    PLATEN_MAX_WIDTH_ESCL_UNITS,
    PLATEN_MAX_WIDTH_INCHES,
    PLATEN_MAX_WIDTH_MILLIMETERS,
    SUPPORTED_PAPER_SIZE_KEYS,
    PaperSizeSpec,
    ResolvedScanRegion,
    inches_to_escl_units,
    inches_to_millimeters,
    inches_to_pixels,
    inches_to_points,
    millimeters_to_inches,
    millimeters_to_pixels,
    millimeters_to_points,
    resolve_scan_region,
)
from white_pepper.algorithms.ocr_orientation import (
    detect_upright_orientation_angle,
    rotate_image_to_upright,
)

__all__: list[str] = [
    "ID1_WIDTH_MILLIMETERS",
    "ID1_HEIGHT_MILLIMETERS",
    "ID1_CORNER_RADIUS_MILLIMETERS",
    "PLATEN_MAX_WIDTH_INCHES",
    "PLATEN_MAX_HEIGHT_INCHES",
    "PLATEN_MAX_WIDTH_MILLIMETERS",
    "PLATEN_MAX_HEIGHT_MILLIMETERS",
    "PLATEN_MAX_WIDTH_ESCL_UNITS",
    "PLATEN_MAX_HEIGHT_ESCL_UNITS",
    "PaperSizeSpec",
    "PAPER_SIZE_REGISTRY",
    "SUPPORTED_PAPER_SIZE_KEYS",
    "ResolvedScanRegion",
    "resolve_scan_region",
    "millimeters_to_inches",
    "inches_to_millimeters",
    "inches_to_points",
    "millimeters_to_points",
    "inches_to_pixels",
    "millimeters_to_pixels",
    "inches_to_escl_units",
    "CardExtractionResult",
    "extract_and_deskew_id_card",
    "BookletPageSegment",
    "segment_booklet_spread",
    "detect_upright_orientation_angle",
    "rotate_image_to_upright",
]
