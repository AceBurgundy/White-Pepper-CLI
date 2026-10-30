"""
Geometric constants, paper size specifications, platen region resolution, and unit conversions.

This module provides physical dimensional constants for ISO/ANSI paper standards,
ID-1 card dimensions, flatbed scanner platen envelopes, and deterministic bounding-box
resolution with safe hardware clamping.
"""

from __future__ import annotations

# eSCL = Enhanced Scanner Client Language
# DPI = Dots Per Inch
# PDF = Portable Document Format
# ID-1 = Identification Card Format 1 (ISO/IEC 7810)
# CLI = Command Line Interface
# GUI = Graphical User Interface

from dataclasses import dataclass
from typing import Optional

ID1_WIDTH_MILLIMETERS: float = 85.60
ID1_HEIGHT_MILLIMETERS: float = 53.98
ID1_CORNER_RADIUS_MILLIMETERS: float = 3.18

MILLIMETERS_PER_INCH: float = 25.4
POINTS_PER_INCH: float = 72.0
ESCL_UNITS_PER_INCH: float = 300.0

PLATEN_MAX_WIDTH_INCHES: float = 8.50
PLATEN_MAX_HEIGHT_INCHES: float = 11.693
PLATEN_MAX_WIDTH_MILLIMETERS: float = 215.90
PLATEN_MAX_HEIGHT_MILLIMETERS: float = 297.00
PLATEN_MAX_WIDTH_ESCL_UNITS: int = 2550
PLATEN_MAX_HEIGHT_ESCL_UNITS: int = 3508
PLATEN_MIN_DIMENSION_INCHES: float = 0.25


def millimeters_to_inches(dimension_millimeters: float) -> float:
    """
    Convert a linear measurement from millimeters to inches.

    Parameters
    ----------
    dimension_millimeters : float
        Linear measurement in millimeters.

    Returns
    -------
    float
        Equivalent linear measurement in inches.
    """
    dimension_inches: float = dimension_millimeters / MILLIMETERS_PER_INCH
    return dimension_inches


def inches_to_millimeters(dimension_inches: float) -> float:
    """
    Convert a linear measurement from inches to millimeters.

    Parameters
    ----------
    dimension_inches : float
        Linear measurement in inches.

    Returns
    -------
    float
        Equivalent linear measurement in millimeters.
    """
    dimension_millimeters: float = dimension_inches * MILLIMETERS_PER_INCH
    return dimension_millimeters


def inches_to_points(dimension_inches: float) -> float:
    """
    Convert a linear measurement from inches to PDF typographic points (72 pt/in).

    Parameters
    ----------
    dimension_inches : float
        Linear measurement in inches.

    Returns
    -------
    float
        Equivalent linear measurement in PDF points.
    """
    dimension_points: float = dimension_inches * POINTS_PER_INCH
    return dimension_points


def millimeters_to_points(dimension_millimeters: float) -> float:
    """
    Convert a linear measurement from millimeters to PDF typographic points.

    Parameters
    ----------
    dimension_millimeters : float
        Linear measurement in millimeters.

    Returns
    -------
    float
        Equivalent linear measurement in PDF points.
    """
    dimension_inches: float = millimeters_to_inches(dimension_millimeters)
    dimension_points: float = inches_to_points(dimension_inches)
    return dimension_points


def inches_to_pixels(dimension_inches: float, resolution_dpi: int) -> int:
    """
    Convert a linear measurement in inches to discrete raster pixels at a target DPI.

    Parameters
    ----------
    dimension_inches : float
        Linear measurement in inches.
    resolution_dpi : int
        Optical or target raster resolution in dots per inch.

    Returns
    -------
    int
        Rounded pixel count corresponding to the physical dimension.
    """
    pixel_count: int = int(round(dimension_inches * float(resolution_dpi)))
    return pixel_count


def millimeters_to_pixels(dimension_millimeters: float, resolution_dpi: int) -> int:
    """
    Convert a linear measurement in millimeters to discrete raster pixels at a target DPI.

    Parameters
    ----------
    dimension_millimeters : float
        Linear measurement in millimeters.
    resolution_dpi : int
        Optical or target raster resolution in dots per inch.

    Returns
    -------
    int
        Rounded pixel count corresponding to the physical dimension.
    """
    dimension_inches: float = millimeters_to_inches(dimension_millimeters)
    pixel_count: int = inches_to_pixels(dimension_inches, resolution_dpi)
    return pixel_count


def inches_to_escl_units(dimension_inches: float) -> int:
    """
    Convert a linear measurement in inches to eSCL coordinate units (1/300th of an inch).

    Parameters
    ----------
    dimension_inches : float
        Linear measurement in inches.

    Returns
    -------
    int
        Rounded coordinate count in eSCL 300-DPI units.
    """
    escl_units: int = int(round(dimension_inches * ESCL_UNITS_PER_INCH))
    return escl_units


@dataclass(frozen=True)
class PaperSizeSpec:
    """
    Immutable physical specification for a standard or specialty paper format.

    Attributes
    ----------
    key : str
        Canonical lowercase CLI/configuration identifier (e.g., ``"a4"``).
    display_name : str
        Human-readable label suitable for GUI combo boxes and documentation.
    width_millimeters : float
        Nominal portrait width in millimeters.
    height_millimeters : float
        Nominal portrait height in millimeters.
    """

    key: str
    display_name: str
    width_millimeters: float
    height_millimeters: float

    @property
    def width_inches(self) -> float:
        """
        Return the nominal portrait width in inches.

        Returns
        -------
        float
            Nominal width in inches.
        """
        converted_width: float = millimeters_to_inches(self.width_millimeters)
        return converted_width

    @property
    def height_inches(self) -> float:
        """
        Return the nominal portrait height in inches.

        Returns
        -------
        float
            Nominal height in inches.
        """
        converted_height: float = millimeters_to_inches(self.height_millimeters)
        return converted_height

    @property
    def width_points(self) -> float:
        """
        Return the nominal portrait width in PDF points.

        Returns
        -------
        float
            Nominal width in PDF points (72 points per inch).
        """
        converted_points: float = millimeters_to_points(self.width_millimeters)
        return converted_points

    @property
    def height_points(self) -> float:
        """
        Return the nominal portrait height in PDF points.

        Returns
        -------
        float
            Nominal height in PDF points (72 points per inch).
        """
        converted_points: float = millimeters_to_points(self.height_millimeters)
        return converted_points


PAPER_SIZE_REGISTRY: dict[str, PaperSizeSpec] = {
    "full": PaperSizeSpec(
        key="full",
        display_name="Full Platen (8.5 x 11.69 in)",
        width_millimeters=215.90,
        height_millimeters=297.00,
    ),
    "a4": PaperSizeSpec(
        key="a4",
        display_name="ISO A4 (210 x 297 mm)",
        width_millimeters=210.00,
        height_millimeters=297.00,
    ),
    "letter": PaperSizeSpec(
        key="letter",
        display_name="US Letter (8.5 x 11.0 in)",
        width_millimeters=215.90,
        height_millimeters=279.40,
    ),
    "legal": PaperSizeSpec(
        key="legal",
        display_name="US Legal (8.5 x 14.0 in)",
        width_millimeters=215.90,
        height_millimeters=355.60,
    ),
    "a5": PaperSizeSpec(
        key="a5",
        display_name="ISO A5 (148 x 210 mm)",
        width_millimeters=148.00,
        height_millimeters=210.00,
    ),
    "a6": PaperSizeSpec(
        key="a6",
        display_name="ISO A6 (105 x 148 mm)",
        width_millimeters=105.00,
        height_millimeters=148.00,
    ),
    "b5": PaperSizeSpec(
        key="b5",
        display_name="ISO B5 (176 x 250 mm)",
        width_millimeters=176.00,
        height_millimeters=250.00,
    ),
    "executive": PaperSizeSpec(
        key="executive",
        display_name="Executive (7.25 x 10.5 in)",
        width_millimeters=184.15,
        height_millimeters=266.70,
    ),
    "statement": PaperSizeSpec(
        key="statement",
        display_name="Statement / Half-Letter (5.5 x 8.5 in)",
        width_millimeters=139.70,
        height_millimeters=215.90,
    ),
    "photo-4x6": PaperSizeSpec(
        key="photo-4x6",
        display_name="Photo 4x6 in (102 x 152 mm)",
        width_millimeters=101.60,
        height_millimeters=152.40,
    ),
    "photo-5x7": PaperSizeSpec(
        key="photo-5x7",
        display_name="Photo 5x7 in (127 x 178 mm)",
        width_millimeters=127.00,
        height_millimeters=177.80,
    ),
    "index-3x5": PaperSizeSpec(
        key="index-3x5",
        display_name="Index Card 3x5 in (76 x 127 mm)",
        width_millimeters=76.20,
        height_millimeters=127.00,
    ),
    "id-card": PaperSizeSpec(
        key="id-card",
        display_name="ID-1 Card Capture Box (5.0 x 5.0 in)",
        width_millimeters=127.00,
        height_millimeters=127.00,
    ),
    "receipt-half": PaperSizeSpec(
        key="receipt-half",
        display_name="Receipt Half-Platen (8.5 x 5.85 in)",
        width_millimeters=215.90,
        height_millimeters=148.50,
    ),
}

SUPPORTED_PAPER_SIZE_KEYS: tuple[str, ...] = tuple(PAPER_SIZE_REGISTRY.keys()) + ("custom",)


@dataclass(frozen=True)
class ResolvedScanRegion:
    """
    Hardware-validated flatbed scan bounding box across physical and protocol units.

    Attributes
    ----------
    paper_size_key : str
        Resolved paper size key (e.g., ``"a4"``, ``"legal"``, or ``"custom"``).
    page_orientation : str
        Resolved orientation (``"portrait"`` or ``"landscape"``).
    offset_x_millimeters : float
        Horizontal origin offset from platen top-left in millimeters.
    offset_y_millimeters : float
        Vertical origin offset from platen top-left in millimeters.
    width_millimeters : float
        Clamped capture width in millimeters.
    height_millimeters : float
        Clamped capture height in millimeters.
    offset_x_inches : float
        Horizontal origin offset in inches.
    offset_y_inches : float
        Vertical origin offset in inches.
    width_inches : float
        Clamped capture width in inches.
    height_inches : float
        Clamped capture height in inches.
    offset_x_points : float
        Horizontal origin offset in PDF points.
    offset_y_points : float
        Vertical origin offset in PDF points.
    width_points : float
        Clamped capture width in PDF points.
    height_points : float
        Clamped capture height in PDF points.
    offset_x_escl_units : int
        Horizontal origin offset in eSCL 1/300-inch units.
    offset_y_escl_units : int
        Vertical origin offset in eSCL 1/300-inch units.
    width_escl_units : int
        Clamped capture width in eSCL 1/300-inch units.
    height_escl_units : int
        Clamped capture height in eSCL 1/300-inch units.
    horizontal_fraction : float
        Ratio of capture width relative to maximum platen width ``[0.0, 1.0]``.
    vertical_fraction : float
        Ratio of capture height relative to maximum platen height ``[0.0, 1.0]``.
    is_full_platen : bool
        ``True`` when the region covers the full physical platen without offset.
    was_clamped : bool
        ``True`` when the requested dimensions or offsets exceeded hardware platen bounds.
    clamping_notice : str
        Human-readable explanation when clamping occurred, or empty string otherwise.
    """

    paper_size_key: str
    page_orientation: str
    offset_x_millimeters: float
    offset_y_millimeters: float
    width_millimeters: float
    height_millimeters: float
    offset_x_inches: float
    offset_y_inches: float
    width_inches: float
    height_inches: float
    offset_x_points: float
    offset_y_points: float
    width_points: float
    height_points: float
    offset_x_escl_units: int
    offset_y_escl_units: int
    width_escl_units: int
    height_escl_units: int
    horizontal_fraction: float
    vertical_fraction: float
    is_full_platen: bool
    was_clamped: bool
    clamping_notice: str

    def pixel_bounds(self, resolution_dpi: int) -> tuple[int, int, int, int]:
        """
        Compute discrete pixel crop coordinates at a given optical DPI.

        Parameters
        ----------
        resolution_dpi : int
            Scanner raster resolution in dots per inch.

        Returns
        -------
        tuple[int, int, int, int]
            Four-element tuple ``(start_x_px, start_y_px, width_px, height_px)``.
        """
        horizontal_start_pixels: int = max(0, inches_to_pixels(self.offset_x_inches, resolution_dpi))
        vertical_start_pixels: int = max(0, inches_to_pixels(self.offset_y_inches, resolution_dpi))
        width_pixels: int = max(1, inches_to_pixels(self.width_inches, resolution_dpi))
        height_pixels: int = max(1, inches_to_pixels(self.height_inches, resolution_dpi))
        return (horizontal_start_pixels, vertical_start_pixels, width_pixels, height_pixels)


def resolve_scan_region(
    paper_size: str = "full",
    area_mode: str = "full",
    page_orientation: str = "portrait",
    custom_width: Optional[float] = None,
    custom_height: Optional[float] = None,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    measurement_unit: str = "mm",
) -> ResolvedScanRegion:
    """
    Resolve paper size presets, orientations, offsets, and custom dimensions into a platen region.

    Parameters
    ----------
    paper_size : str, optional
        Paper size identifier from ``PAPER_SIZE_REGISTRY`` or ``"custom"``, by default ``"full"``.
    area_mode : str, optional
        Legacy area modifier (``"full"``, ``"half"``, or ``"quarter-tl"``), by default ``"full"``.
    page_orientation : str, optional
        Page orientation (``"portrait"`` or ``"landscape"``), by default ``"portrait"``.
    custom_width : Optional[float], optional
        Explicit capture width in ``measurement_unit`` when using custom sizing, by default ``None``.
    custom_height : Optional[float], optional
        Explicit capture height in ``measurement_unit`` when using custom sizing, by default ``None``.
    offset_x : float, optional
        Horizontal origin offset from top-left glass corner in ``measurement_unit``, by default ``0.0``.
    offset_y : float, optional
        Vertical origin offset from top-left glass corner in ``measurement_unit``, by default ``0.0``.
    measurement_unit : str, optional
        Unit system for ``custom_width``, ``custom_height``, ``offset_x``, and ``offset_y``
        (``"mm"`` or ``"in"``), by default ``"mm"``.

    Returns
    -------
    ResolvedScanRegion
        Validated and hardware-clamped flatbed scan geometry specification.

    Raises
    ------
    ValueError
        If an unsupported paper size, orientation, unit, negative offset, or non-positive
        custom dimension is supplied.
    """
    normalized_unit: str = measurement_unit.strip().lower()
    if normalized_unit not in ("mm", "in"):
        raise ValueError(
            f"Unsupported measurement unit '{measurement_unit}'. Expected 'mm' or 'in'."
        )

    normalized_orientation: str = page_orientation.strip().lower()
    if normalized_orientation not in ("portrait", "landscape"):
        raise ValueError(
            f"Unsupported page orientation '{page_orientation}'. Expected 'portrait' or 'landscape'."
        )

    normalized_area: str = area_mode.strip().lower()
    if normalized_area not in ("full", "half", "quarter-tl"):
        raise ValueError(
            f"Unsupported area mode '{area_mode}'. Expected 'full', 'half', or 'quarter-tl'."
        )

    if offset_x < 0.0 or offset_y < 0.0:
        raise ValueError(
            f"Scan offsets must be non-negative (received offset_x={offset_x}, offset_y={offset_y})."
        )

    requested_horizontal_offset_inches: float = (
        millimeters_to_inches(offset_x) if normalized_unit == "mm" else offset_x
    )
    requested_vertical_offset_inches: float = (
        millimeters_to_inches(offset_y) if normalized_unit == "mm" else offset_y
    )

    normalized_paper_key: str = paper_size.strip().lower()
    has_explicit_dimensions: bool = (custom_width is not None) or (custom_height is not None)

    requested_width_inches: float
    requested_height_inches: float
    effective_paper_key: str

    if normalized_paper_key == "custom" or has_explicit_dimensions:
        if custom_width is None or custom_height is None:
            raise ValueError(
                "Both custom_width and custom_height must be specified when using custom dimensions."
            )
        if custom_width <= 0.0 or custom_height <= 0.0:
            raise ValueError(
                f"Custom scan dimensions must be strictly positive (received {custom_width} x {custom_height})."
            )
        effective_paper_key = "custom"
        requested_width_inches = (
            millimeters_to_inches(custom_width) if normalized_unit == "mm" else custom_width
        )
        requested_height_inches = (
            millimeters_to_inches(custom_height) if normalized_unit == "mm" else custom_height
        )
        if normalized_orientation == "landscape" and requested_width_inches < requested_height_inches:
            swapped_width_custom: float = requested_height_inches
            swapped_height_custom: float = requested_width_inches
            requested_width_inches = swapped_width_custom
            requested_height_inches = swapped_height_custom
    else:
        if normalized_paper_key not in PAPER_SIZE_REGISTRY:
            valid_choices_text: str = ", ".join(SUPPORTED_PAPER_SIZE_KEYS)
            raise ValueError(
                f"Unknown paper size '{paper_size}'. Supported choices: {valid_choices_text}."
            )
        paper_spec: PaperSizeSpec = PAPER_SIZE_REGISTRY[normalized_paper_key]
        effective_paper_key = paper_spec.key
        requested_width_inches = paper_spec.width_inches
        requested_height_inches = paper_spec.height_inches

        if normalized_orientation == "landscape":
            swapped_width_preset: float = requested_height_inches
            swapped_height_preset: float = requested_width_inches
            requested_width_inches = swapped_width_preset
            requested_height_inches = swapped_height_preset

        if effective_paper_key == "full":
            if normalized_area == "half":
                requested_height_inches = PLATEN_MAX_HEIGHT_INCHES / 2.0
                effective_paper_key = "receipt-half"
            elif normalized_area == "quarter-tl":
                requested_width_inches = PLATEN_MAX_WIDTH_INCHES / 2.0
                requested_height_inches = PLATEN_MAX_HEIGHT_INCHES / 2.0

    tolerance_inches: float = 0.002
    clamping_reasons: list[str] = []

    maximum_allowed_horizontal_offset: float = PLATEN_MAX_WIDTH_INCHES - PLATEN_MIN_DIMENSION_INCHES
    maximum_allowed_vertical_offset: float = PLATEN_MAX_HEIGHT_INCHES - PLATEN_MIN_DIMENSION_INCHES

    clamped_horizontal_offset_inches: float = min(
        requested_horizontal_offset_inches, maximum_allowed_horizontal_offset
    )
    clamped_vertical_offset_inches: float = min(
        requested_vertical_offset_inches, maximum_allowed_vertical_offset
    )

    if requested_horizontal_offset_inches - clamped_horizontal_offset_inches > tolerance_inches:
        clamping_reasons.append(
            f"X offset clamped from {requested_horizontal_offset_inches:.2f} in to {clamped_horizontal_offset_inches:.2f} in"
        )
    if requested_vertical_offset_inches - clamped_vertical_offset_inches > tolerance_inches:
        clamping_reasons.append(
            f"Y offset clamped from {requested_vertical_offset_inches:.2f} in to {clamped_vertical_offset_inches:.2f} in"
        )

    available_width_inches: float = PLATEN_MAX_WIDTH_INCHES - clamped_horizontal_offset_inches
    available_height_inches: float = PLATEN_MAX_HEIGHT_INCHES - clamped_vertical_offset_inches

    clamped_width_inches: float = max(
        PLATEN_MIN_DIMENSION_INCHES,
        min(requested_width_inches, available_width_inches),
    )
    clamped_height_inches: float = max(
        PLATEN_MIN_DIMENSION_INCHES,
        min(requested_height_inches, available_height_inches),
    )

    if requested_width_inches - clamped_width_inches > tolerance_inches:
        clamping_reasons.append(
            f"width clamped from {requested_width_inches:.2f} in to {clamped_width_inches:.2f} in"
        )
    if requested_height_inches - clamped_height_inches > tolerance_inches:
        clamping_reasons.append(
            f"height clamped from {requested_height_inches:.2f} in to {clamped_height_inches:.2f} in"
        )

    was_clamped: bool = len(clamping_reasons) > 0
    clamping_notice: str = ""
    if was_clamped:
        joined_reasons: str = "; ".join(clamping_reasons)
        clamping_notice = (
            f"Requested '{effective_paper_key}' ({normalized_orientation}) exceeds physical platen "
            f"envelope ({PLATEN_MAX_WIDTH_INCHES:.2f} x {PLATEN_MAX_HEIGHT_INCHES:.2f} in): "
            f"{joined_reasons}."
        )

    horizontal_offset_escl: int = max(
        0,
        min(PLATEN_MAX_WIDTH_ESCL_UNITS - 8, inches_to_escl_units(clamped_horizontal_offset_inches)),
    )
    vertical_offset_escl: int = max(
        0,
        min(PLATEN_MAX_HEIGHT_ESCL_UNITS - 8, inches_to_escl_units(clamped_vertical_offset_inches)),
    )
    width_escl: int = max(
        8,
        min(PLATEN_MAX_WIDTH_ESCL_UNITS - horizontal_offset_escl, inches_to_escl_units(clamped_width_inches)),
    )
    height_escl: int = max(
        8,
        min(
            PLATEN_MAX_HEIGHT_ESCL_UNITS - vertical_offset_escl,
            inches_to_escl_units(clamped_height_inches),
        ),
    )

    horizontal_fraction: float = min(
        1.0,
        max(0.01, (clamped_horizontal_offset_inches + clamped_width_inches) / PLATEN_MAX_WIDTH_INCHES),
    )
    vertical_fraction: float = min(
        1.0,
        max(0.01, (clamped_vertical_offset_inches + clamped_height_inches) / PLATEN_MAX_HEIGHT_INCHES),
    )

    is_full_platen: bool = (
        clamped_horizontal_offset_inches <= tolerance_inches
        and clamped_vertical_offset_inches <= tolerance_inches
        and abs(clamped_width_inches - PLATEN_MAX_WIDTH_INCHES) <= 0.01
        and abs(clamped_height_inches - PLATEN_MAX_HEIGHT_INCHES) <= 0.01
    )

    resolved_region: ResolvedScanRegion = ResolvedScanRegion(
        paper_size_key=effective_paper_key,
        page_orientation=normalized_orientation,
        offset_x_millimeters=inches_to_millimeters(clamped_horizontal_offset_inches),
        offset_y_millimeters=inches_to_millimeters(clamped_vertical_offset_inches),
        width_millimeters=inches_to_millimeters(clamped_width_inches),
        height_millimeters=inches_to_millimeters(clamped_height_inches),
        offset_x_inches=clamped_horizontal_offset_inches,
        offset_y_inches=clamped_vertical_offset_inches,
        width_inches=clamped_width_inches,
        height_inches=clamped_height_inches,
        offset_x_points=inches_to_points(clamped_horizontal_offset_inches),
        offset_y_points=inches_to_points(clamped_vertical_offset_inches),
        width_points=inches_to_points(clamped_width_inches),
        height_points=inches_to_points(clamped_height_inches),
        offset_x_escl_units=horizontal_offset_escl,
        offset_y_escl_units=vertical_offset_escl,
        width_escl_units=width_escl,
        height_escl_units=height_escl,
        horizontal_fraction=horizontal_fraction,
        vertical_fraction=vertical_fraction,
        is_full_platen=is_full_platen,
        was_clamped=was_clamped,
        clamping_notice=clamping_notice,
    )
    return resolved_region
