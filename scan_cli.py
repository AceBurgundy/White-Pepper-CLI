"""
Centralized Scanner Acquisition CLI.

Provides unified command-line control for multi-protocol flatbed scanning,
paper size and custom platen geometry selection, discrete optical DPIs,
color modes, tone/rotation adjustments, ID-1 card acquisition, and continuous
batch interval sessions.
"""

from __future__ import annotations

# CLI = Command Line Interface
# eSCL = Enhanced Scanner Client Language
# WIA = Windows Image Acquisition
# USB = Universal Serial Bus
# DPI = Dots Per Inch
# PDF = Portable Document Format
# ID-1 = Identification Card Format 1 (ISO/IEC 7810)
# RGB = Red Green Blue
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format
# HTTP = Hypertext Transfer Protocol
# TCP = Transmission Control Protocol
# IP = Internet Protocol

import argparse
from pathlib import Path
import sys
from typing import Optional

import cv2
import numpy as np

from white_pepper.algorithms.card_vision import (
    CardExtractionResult,
    composite_card_onto_background,
    extract_and_deskew_id_card,
)
from white_pepper.algorithms.legal_vision import (
    LegalStitchResult,
    save_legal_stitch_result_to_pdf,
    stitch_legal_two_pass,
)
from white_pepper.algorithms.geometry import (
    ID1_CORNER_RADIUS_MILLIMETERS,
    SUPPORTED_PAPER_SIZE_KEYS,
    ResolvedScanRegion,
)
from white_pepper.config import (
    SUPPORTED_BACKEND_MODES,
    SUPPORTED_CARD_BACKGROUNDS,
    SUPPORTED_COLOR_MODES,
    SUPPORTED_DPI_VALUES,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_ROTATION_ANGLES,
    ScanConfiguration,
)
from white_pepper.hardware.escl_client import (
    DEFAULT_ESCL_IP,
    DEFAULT_ESCL_PORT,
    apply_post_scan_adjustments_and_save,
)
from white_pepper.hardware.scanner_manager import ScannerManager
from white_pepper.utils.console import (
    display_countdown,
    wait_for_spacebar,
)

FLATBED_PRESET_CHOICES: tuple[str, ...] = (
    "boy-gatas-receipts",
    "normal-scan",
    "max-scan",
    "a4-document",
    "letter-document",
    "photo-4x6",
    "archive-photo",
    "fast-document",
    "id-card-raw",
)


def _attach_shared_connection_flags(
    target_parser: argparse.ArgumentParser,
    use_suppress_defaults: bool = False,
) -> None:
    """
    Attach shared scanner connection and global output arguments to a parser.

    Parameters
    ----------
    target_parser : argparse.ArgumentParser
        Parser or subparser receiving the connection flags.
    use_suppress_defaults : bool, optional
        Use ``argparse.SUPPRESS`` so subparser flags do not clobber root flags when omitted,
        by default ``False``.

    Returns
    -------
    None
    """
    default_host_address: object = (
        argparse.SUPPRESS if use_suppress_defaults else DEFAULT_ESCL_IP
    )
    default_port_number: object = (
        argparse.SUPPRESS if use_suppress_defaults else DEFAULT_ESCL_PORT
    )
    default_output_directory: object = (
        argparse.SUPPRESS if use_suppress_defaults else r"D:\Pictures\Scanned"
    )
    default_backend_mode: object = (
        argparse.SUPPRESS if use_suppress_defaults else "auto"
    )
    default_boolean_flag: object = (
        argparse.SUPPRESS if use_suppress_defaults else False
    )

    target_parser.add_argument(
        "--ip",
        "--host",
        dest="escl_ip",
        type=str,
        default=default_host_address,
        help="IPv4 address or hostname of wireless eSCL scanner (default: 192.168.1.150).",
    )
    target_parser.add_argument(
        "--port",
        dest="escl_port",
        type=int,
        default=default_port_number,
        help="HTTP TCP port of wireless eSCL scanner (default: 8080).",
    )
    target_parser.add_argument(
        "--output-dir",
        dest="output_directory",
        type=str,
        default=default_output_directory,
        help="Root output directory for scanned files (default: D:\\Pictures\\Scanned).",
    )
    target_parser.add_argument(
        "--backend",
        dest="backend_mode",
        choices=list(SUPPORTED_BACKEND_MODES),
        default=default_backend_mode,
        help="Scanner transport backend: auto, escl, wia, or powershell (default: auto).",
    )
    target_parser.add_argument(
        "--usb-only",
        dest="usb_only",
        action="store_true",
        default=default_boolean_flag,
        help="Bypass wireless eSCL and force local USB WIA acquisition.",
    )
    target_parser.add_argument(
        "--no-beep",
        dest="disable_beep",
        action="store_true",
        default=default_boolean_flag,
        help="Mute acoustic completion beeps during scanning.",
    )
    target_parser.add_argument(
        "--device-id",
        dest="device_id",
        type=str,
        default=argparse.SUPPRESS if use_suppress_defaults else None,
        help="Optional Windows Image Acquisition (WIA) hardware DeviceID to target a specific USB scanner.",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Construct the command-line argument parser for ``scan_cli``.

    Returns
    -------
    argparse.ArgumentParser
        Configured root argument parser with ``flatbed``, ``card``, and ``booklet`` subcommands.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="scan_cli",
        description="Unified Hardware Scanner Acquisition CLI for white-pepper.",
        add_help=True,
    )
    _attach_shared_connection_flags(parser, use_suppress_defaults=False)

    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command",
        help="Acquisition command to run.",
    )

    flatbed_parser: argparse.ArgumentParser = subparsers.add_parser(
        "flatbed",
        help="Flexible flatbed document, photo, and receipt scanning.",
    )
    _attach_shared_connection_flags(flatbed_parser, use_suppress_defaults=True)

    flatbed_parser.add_argument(
        "preset",
        nargs="?",
        default=None,
        choices=list(FLATBED_PRESET_CHOICES),
        help="Optional workflow preset shortcut.",
    )
    flatbed_parser.add_argument(
        "--preset",
        dest="named_preset",
        choices=list(FLATBED_PRESET_CHOICES),
        default=None,
        help="Named workflow preset shortcut (alternative to positional preset).",
    )
    flatbed_parser.add_argument(
        "--paper-size",
        dest="paper_size",
        choices=list(SUPPORTED_PAPER_SIZE_KEYS),
        default=None,
        help="Target paper size preset or 'custom' (e.g., full, a4, letter, legal, a5, photo-4x6, receipt-half).",
    )
    flatbed_parser.add_argument(
        "--area",
        dest="area_mode",
        choices=["full", "half", "quarter-tl"],
        default=None,
        help="Legacy platen area selector: full (100%% platen), half (50%% receipt platen), or quarter-tl.",
    )
    flatbed_parser.add_argument(
        "--page-orientation",
        dest="page_orientation",
        choices=["portrait", "landscape"],
        default="portrait",
        help="Scan paper orientation on the platen glass (default: portrait).",
    )
    flatbed_parser.add_argument(
        "--width",
        dest="custom_width",
        type=float,
        default=None,
        help="Custom scan width in --units (mm or in). Promotes paper-size to 'custom'.",
    )
    flatbed_parser.add_argument(
        "--height",
        dest="custom_height",
        type=float,
        default=None,
        help="Custom scan height in --units (mm or in). Promotes paper-size to 'custom'.",
    )
    flatbed_parser.add_argument(
        "--offset-x",
        dest="offset_x",
        type=float,
        default=0.0,
        help="Horizontal start offset from top-left platen corner in --units (default: 0.0).",
    )
    flatbed_parser.add_argument(
        "--offset-y",
        dest="offset_y",
        type=float,
        default=0.0,
        help="Vertical start offset from top-left platen corner in --units (default: 0.0).",
    )
    flatbed_parser.add_argument(
        "--units",
        dest="measurement_unit",
        choices=["mm", "in"],
        default="mm",
        help="Measurement unit for --width, --height, --offset-x, and --offset-y (default: mm).",
    )
    flatbed_parser.add_argument(
        "--dpi",
        dest="resolution_dpi",
        type=int,
        choices=list(SUPPORTED_DPI_VALUES),
        default=None,
        help="Discrete optical scan resolution in DPI: 75, 100, 200, 300, 600, or 1200.",
    )
    flatbed_parser.add_argument(
        "--quality",
        dest="quality_mode",
        choices=["std", "max", "draft", "full"],
        default=None,
        help="Legacy quality alias: std (300 DPI), max/full (1200 DPI), or draft (100 DPI).",
    )
    flatbed_parser.add_argument(
        "--color-mode",
        dest="color_mode",
        choices=list(SUPPORTED_COLOR_MODES),
        default=None,
        help="Channel mode: color (24-bit RGB), grayscale (8-bit), or bw (1-bit binary).",
    )
    flatbed_parser.add_argument(
        "--intent",
        dest="intent_type",
        choices=[
            "document",
            "photo",
            "text-and-graphic",
            "preview",
            "Document",
            "Photo",
            "TextAndGraphic",
            "Preview",
        ],
        default=None,
        help="Hardware scan intent hint (document, photo, text-and-graphic, preview).",
    )
    flatbed_parser.add_argument(
        "--format",
        dest="output_format",
        choices=list(SUPPORTED_IMAGE_FORMATS),
        default=None,
        help="Output file format: png, jpg, jpeg, tiff, bmp, or pdf (default: png).",
    )
    flatbed_parser.add_argument(
        "--jpeg-quality",
        dest="jpeg_quality",
        type=int,
        default=92,
        help="JPEG encoding quality from 1 to 100 when saving jpg or compressed pdf (default: 92).",
    )
    flatbed_parser.add_argument(
        "--brightness",
        dest="brightness",
        type=int,
        default=0,
        help="Relative brightness adjustment from -100 to 100 (default: 0).",
    )
    flatbed_parser.add_argument(
        "--contrast",
        dest="contrast",
        type=int,
        default=0,
        help="Relative contrast adjustment from -100 to 100 (default: 0).",
    )
    flatbed_parser.add_argument(
        "--rotate",
        dest="rotation_degrees",
        type=int,
        choices=list(SUPPORTED_ROTATION_ANGLES),
        default=0,
        help="Clockwise post-scan rotation angle in degrees: 0, 90, 180, or 270 (default: 0).",
    )
    flatbed_parser.add_argument(
        "--auto-crop",
        dest="auto_crop_whitespace",
        action="store_true",
        default=False,
        help="Automatically crop uniform white borders around scanned content.",
    )
    flatbed_parser.add_argument(
        "--folder",
        dest="subfolder_name",
        type=str,
        default=None,
        help="Optional subfolder inside --output-dir (e.g., boy-gatas-receipts).",
    )
    flatbed_parser.add_argument(
        "--prefix",
        dest="filename_prefix",
        type=str,
        default=None,
        help="Filename prefix for auto-generated scan files (default: scan).",
    )
    flatbed_parser.add_argument(
        "--interval",
        dest="interval_seconds",
        type=float,
        default=None,
        help="Delay in seconds between repeated batch scans (omit for single scan).",
    )
    flatbed_parser.add_argument(
        "--max-scans",
        dest="max_scans",
        type=int,
        default=0,
        help="Maximum number of scans in continuous interval mode (0 = unlimited until Ctrl+C).",
    )
    flatbed_parser.add_argument(
        "--start-delay",
        dest="start_delay_seconds",
        type=float,
        default=0.0,
        help="Initial countdown delay in seconds before the first scan starts (default: 0).",
    )

    card_parser: argparse.ArgumentParser = subparsers.add_parser(
        "card",
        help="ID-1 card scanning with 5x5 inch platen capture, deskewing, and corner masking.",
    )
    _attach_shared_connection_flags(card_parser, use_suppress_defaults=True)
    card_parser.add_argument(
        "--resolution",
        "--dpi",
        dest="card_resolution_dpi",
        type=int,
        choices=list(SUPPORTED_DPI_VALUES),
        default=300,
        help="Card scan optical resolution in DPI (default: 300).",
    )
    card_parser.add_argument(
        "--color-mode",
        dest="color_mode",
        choices=list(SUPPORTED_COLOR_MODES),
        default="color",
        help="Card color mode: color, grayscale, or bw (default: color).",
    )
    card_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["png", "jpg", "jpeg", "tiff", "bmp"],
        default="png",
        help="Extracted card image format (default: png).",
    )
    card_parser.add_argument(
        "--jpeg-quality",
        dest="jpeg_quality",
        type=int,
        default=95,
        help="JPEG quality factor from 1 to 100 when saving as jpg (default: 95).",
    )
    card_parser.add_argument(
        "--safety-inset-mm",
        "--padding",
        dest="safety_inset_mm",
        type=float,
        default=0.5,
        help="Card edge safety inset in millimeters (default: 0.5).",
    )
    card_parser.add_argument(
        "--corner-radius-mm",
        "--corner-radius",
        dest="corner_radius_mm",
        type=float,
        default=ID1_CORNER_RADIUS_MILLIMETERS,
        help="ID-1 rounded corner radius in millimeters (default: 3.18).",
    )
    card_parser.add_argument(
        "--background",
        dest="background_mode",
        choices=list(SUPPORTED_CARD_BACKGROUNDS),
        default="transparent",
        help="Corner background fill: transparent, white, or black (default: transparent).",
    )
    card_parser.add_argument(
        "--no-deskew",
        dest="skip_deskew",
        action="store_true",
        default=False,
        help="Save raw 5x5 inch capture without computer vision deskewing.",
    )
    card_parser.add_argument(
        "--no-prompt",
        dest="skip_prompt",
        action="store_true",
        default=False,
        help="Start scanning immediately without waiting for interactive SPACEBAR press.",
    )
    card_parser.add_argument(
        "--prefix",
        "--name",
        dest="card_filename_prefix",
        type=str,
        default="card",
        help="Filename prefix for extracted card output (default: card).",
    )

    booklet_parser: argparse.ArgumentParser = subparsers.add_parser(
        "booklet",
        help="Continuous booklet spread scanning with configurable paper size and countdowns.",
    )
    _attach_shared_connection_flags(booklet_parser, use_suppress_defaults=True)
    booklet_parser.add_argument(
        "--paper-size",
        dest="paper_size",
        choices=list(SUPPORTED_PAPER_SIZE_KEYS),
        default="full",
        help="Platen paper size for spread capture (default: full).",
    )
    booklet_parser.add_argument(
        "--dpi",
        dest="resolution_dpi",
        type=int,
        choices=list(SUPPORTED_DPI_VALUES),
        default=300,
        help="Optical scan resolution in DPI (default: 300).",
    )
    booklet_parser.add_argument(
        "--color-mode",
        dest="color_mode",
        choices=list(SUPPORTED_COLOR_MODES),
        default="color",
        help="Color mode: color, grayscale, or bw (default: color).",
    )
    booklet_parser.add_argument(
        "--format",
        dest="output_format",
        choices=list(SUPPORTED_IMAGE_FORMATS),
        default="png",
        help="Spread file format (default: png).",
    )
    booklet_parser.add_argument(
        "--interval",
        dest="booklet_interval_seconds",
        type=int,
        default=10,
        help="Interval delay in seconds between spread captures (default: 10).",
    )
    booklet_parser.add_argument(
        "--max-scans",
        dest="max_scans",
        type=int,
        default=0,
        help="Maximum spreads to capture before stopping automatically (0 = unlimited).",
    )
    booklet_parser.add_argument(
        "--start-delay",
        dest="start_delay_seconds",
        type=int,
        default=0,
        help="Initial countdown delay in seconds before spread #1 (default: 0).",
    )

    legal_stitch_parser: argparse.ArgumentParser = subparsers.add_parser(
        "legal-stitch",
        help="Deterministic two-pass US Legal (8.50\" x 14.00\") scanning and stitching.",
    )
    _attach_shared_connection_flags(legal_stitch_parser, use_suppress_defaults=True)
    legal_stitch_parser.add_argument(
        "--name",
        "--prefix",
        dest="document_name",
        type=str,
        default="Legal_Document",
        help="Target base document filename.",
    )
    legal_stitch_parser.add_argument(
        "--resolution",
        "--dpi",
        dest="resolution_dpi",
        type=int,
        choices=list(SUPPORTED_DPI_VALUES),
        default=300,
        help="Optical scan resolution in DPI (default: 300).",
    )
    legal_stitch_parser.add_argument(
        "--color-mode",
        dest="color_mode",
        choices=list(SUPPORTED_COLOR_MODES),
        default="color",
        help="Color mode: color, grayscale, or bw (default: color).",
    )
    legal_stitch_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["pdf", "png"],
        default="pdf",
        help="Output format: pdf (default) or png.",
    )
    legal_stitch_parser.add_argument(
        "--ipc-mode",
        dest="enable_ipc_mode",
        action="store_true",
        default=False,
        help="Emit structured JSON events on stdout for frontend UI integration.",
    )

    return parser


def resolve_flatbed_scan_configuration(arguments: argparse.Namespace) -> ScanConfiguration:
    """
    Resolve parsed CLI ``flatbed`` arguments into a validated ``ScanConfiguration``.

    Applies the deterministic four-tier precedence hierarchy (`Q-002`):
    ``Standard Defaults < Workflow Preset < Legacy Flags (--quality, --area) < Explicit Granular Flags``.

    Parameters
    ----------
    arguments : argparse.Namespace
        Parsed namespace returned by ``build_argument_parser().parse_args()``.

    Returns
    -------
    ScanConfiguration
        Fully resolved flatbed acquisition configuration contract.

    Raises
    ------
    ValueError
        If ``--paper-size custom`` or partial custom dimensions are supplied without both
        ``--width`` and ``--height``, or if brightness/contrast/JPEG bounds are invalid.
    """
    dpi_value: int = 300
    maximum_quality_flag: bool = False
    paper_size_key: str = "full"
    area_mode_key: str = "full"
    color_mode_key: str = "color"
    intent_key: str = "document"
    format_key: str = "png"
    prefix_value: str = "scan"
    subfolder_value: Optional[str] = None
    interval_value: Optional[float] = None

    active_preset: Optional[str] = getattr(arguments, "named_preset", None) or getattr(
        arguments, "preset", None
    )
    if active_preset == "boy-gatas-receipts":
        dpi_value = 1200
        maximum_quality_flag = True
        paper_size_key = "receipt-half"
        area_mode_key = "half"
        interval_value = 15.0
        subfolder_value = "boy-gatas-receipts"
    elif active_preset == "max-scan":
        dpi_value = 1200
        maximum_quality_flag = True
    elif active_preset == "normal-scan":
        dpi_value = 300
        maximum_quality_flag = False
    elif active_preset == "a4-document":
        paper_size_key = "a4"
        dpi_value = 300
        intent_key = "document"
    elif active_preset == "letter-document":
        paper_size_key = "letter"
        dpi_value = 300
        intent_key = "document"
    elif active_preset in ("photo-4x6", "archive-photo"):
        paper_size_key = "photo-4x6"
        dpi_value = 1200
        maximum_quality_flag = True
        intent_key = "photo"
    elif active_preset == "fast-document":
        paper_size_key = "a4"
        dpi_value = 100
        color_mode_key = "grayscale"
        intent_key = "preview"
    elif active_preset == "id-card-raw":
        paper_size_key = "id-card"
        dpi_value = 600
        intent_key = "photo"

    legacy_quality: Optional[str] = getattr(arguments, "quality_mode", None)
    if legacy_quality is not None:
        if legacy_quality in ("max", "full"):
            dpi_value = 1200
            maximum_quality_flag = True
        elif legacy_quality == "draft":
            dpi_value = 100
            maximum_quality_flag = False
        else:
            dpi_value = 300
            maximum_quality_flag = False

    legacy_area: Optional[str] = getattr(arguments, "area_mode", None)
    if legacy_area is not None:
        area_mode_key = legacy_area
        if legacy_area == "half":
            paper_size_key = "receipt-half"
        elif legacy_area == "full":
            paper_size_key = "full"

    explicit_dpi: Optional[int] = getattr(arguments, "resolution_dpi", None)
    if explicit_dpi is not None:
        dpi_value = explicit_dpi
        maximum_quality_flag = explicit_dpi == 1200

    explicit_paper: Optional[str] = getattr(arguments, "paper_size", None)
    if explicit_paper is not None:
        paper_size_key = explicit_paper
        if explicit_paper != "receipt-half" and legacy_area is None:
            area_mode_key = "full"

    custom_width_value: Optional[float] = getattr(arguments, "custom_width", None)
    custom_height_value: Optional[float] = getattr(arguments, "custom_height", None)
    if paper_size_key == "custom" or custom_width_value is not None or custom_height_value is not None:
        if custom_width_value is None or custom_height_value is None:
            raise ValueError(
                "Custom paper geometry requires both --width and --height to be specified."
            )
        paper_size_key = "custom"

    explicit_color: Optional[str] = getattr(arguments, "color_mode", None)
    if explicit_color is not None:
        color_mode_key = explicit_color

    explicit_intent: Optional[str] = getattr(arguments, "intent_type", None)
    if explicit_intent is not None:
        normalized_intent_map: dict[str, str] = {
            "document": "document",
            "photo": "photo",
            "textandgraphic": "text-and-graphic",
            "text-and-graphic": "text-and-graphic",
            "preview": "preview",
        }
        intent_key = normalized_intent_map.get(explicit_intent.lower(), "document")

    explicit_format: Optional[str] = getattr(arguments, "output_format", None)
    if explicit_format is not None:
        format_key = explicit_format

    explicit_subfolder: Optional[str] = getattr(arguments, "subfolder_name", None)
    if explicit_subfolder is not None:
        subfolder_value = explicit_subfolder

    explicit_prefix: Optional[str] = getattr(arguments, "filename_prefix", None)
    if explicit_prefix is not None:
        prefix_value = explicit_prefix

    explicit_interval: Optional[float] = getattr(arguments, "interval_seconds", None)
    if explicit_interval is not None:
        interval_value = explicit_interval if explicit_interval > 0.0 else None

    brightness_value: int = int(getattr(arguments, "brightness", 0))
    contrast_value: int = int(getattr(arguments, "contrast", 0))
    if not (-100 <= brightness_value <= 100) or not (-100 <= contrast_value <= 100):
        raise ValueError("--brightness and --contrast must lie within [-100, 100].")

    jpeg_quality_value: int = int(getattr(arguments, "jpeg_quality", 92))
    if not (1 <= jpeg_quality_value <= 100):
        raise ValueError("--jpeg-quality must lie within [1, 100].")

    usb_only_flag: bool = bool(getattr(arguments, "usb_only", False))
    requested_backend: str = str(getattr(arguments, "backend_mode", "auto"))
    effective_backend: str = "wia" if (usb_only_flag and requested_backend == "auto") else requested_backend
    prefer_escl_flag: bool = (not usb_only_flag) and (effective_backend in ("auto", "escl"))

    maximum_scans_argument: int = int(getattr(arguments, "max_scans", 0))
    effective_maximum_scans: int = maximum_scans_argument if interval_value is not None else 1

    configuration: ScanConfiguration = ScanConfiguration(
        destination_directory=Path(str(getattr(arguments, "output_directory", r"D:\Pictures\Scanned"))),
        subfolder_name=subfolder_value,
        filename_prefix=prefix_value,
        paper_size=paper_size_key,
        area_mode=area_mode_key,
        page_orientation=str(getattr(arguments, "page_orientation", "portrait")),
        custom_width=custom_width_value,
        custom_height=custom_height_value,
        offset_x=float(getattr(arguments, "offset_x", 0.0)),
        offset_y=float(getattr(arguments, "offset_y", 0.0)),
        measurement_unit=str(getattr(arguments, "measurement_unit", "mm")),
        resolution_dpi=dpi_value,
        maximum_quality=maximum_quality_flag,
        color_mode=color_mode_key,
        intent_type=intent_key,
        output_format=format_key,
        jpeg_quality=jpeg_quality_value,
        brightness=brightness_value,
        contrast=contrast_value,
        rotation_degrees=int(getattr(arguments, "rotation_degrees", 0)),
        auto_crop_whitespace=bool(getattr(arguments, "auto_crop_whitespace", False)),
        interval_seconds=interval_value,
        max_scans=effective_maximum_scans,
        start_delay_seconds=max(0.0, float(getattr(arguments, "start_delay_seconds", 0.0))),
        enable_beep=not bool(getattr(arguments, "disable_beep", False)),
        prefer_escl=prefer_escl_flag,
        backend_mode=effective_backend,
        escl_host=str(getattr(arguments, "escl_ip", DEFAULT_ESCL_IP)),
        escl_port=int(getattr(arguments, "escl_port", DEFAULT_ESCL_PORT)),
        wia_device_id=getattr(arguments, "device_id", None),
    )
    # Validate region geometry eagerly so invalid custom dimensions fail fast
    configuration.resolve_region()
    return configuration


def handle_flatbed_command(
    scanner_manager: ScannerManager,
    arguments: argparse.Namespace,
) -> None:
    """
    Execute the single or continuous flatbed scanning workflow.

    Parameters
    ----------
    scanner_manager : ScannerManager
        Initialized hardware scanner manager.
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    configuration: ScanConfiguration = resolve_flatbed_scan_configuration(arguments)
    resolved_region: ResolvedScanRegion = configuration.resolve_region()
    target_directory: Path = configuration.target_directory()
    target_directory.mkdir(parents=True, exist_ok=True)
    scanner_manager.destination_directory = target_directory

    if resolved_region.was_clamped:
        print(f"[Warning] {resolved_region.clamping_notice}", file=sys.stderr)

    print("--------------------------------------------------")
    print("  white-pepper: Flatbed Acquisition Active")
    print(f"  Resolution : {configuration.effective_dpi()} DPI ({configuration.color_mode}, {configuration.intent_type})")
    print(
        f"  Paper Area : {resolved_region.paper_size_key} ({resolved_region.page_orientation}) — "
        f"{resolved_region.width_millimeters:.1f} x {resolved_region.height_millimeters:.1f} mm "
        f"({resolved_region.width_inches:.2f} x {resolved_region.height_inches:.2f} in)"
    )
    print(f"  Format     : {configuration.normalized_extension().upper()}")
    print(f"  Destination: {target_directory}")
    print("--------------------------------------------------\n")

    initial_delay: int = int(round(configuration.start_delay_seconds))
    if initial_delay > 0:
        display_countdown(initial_delay, action_description="Initial scan starts in")

    if configuration.interval_seconds is None or configuration.interval_seconds <= 0.0:
        saved_file: Path = scanner_manager.acquire_with_config(configuration)
        file_size_megabytes: float = float(saved_file.stat().st_size) / (1024.0 * 1024.0)
        print(f"\n[Success] Scanned file saved: {saved_file} ({file_size_megabytes:.2f} MB)")
        return

    interval_int: int = max(1, int(round(configuration.interval_seconds)))
    limit_note: str = (
        f"max {configuration.max_scans} scans"
        if configuration.max_scans > 0
        else "until Ctrl+C"
    )
    print(f"[Continuous Mode] Repeating scan every {interval_int}s ({limit_note}).\n")

    iteration_number: int = 1
    try:
        while True:
            print(f"[Scan Iteration #{iteration_number}]")
            saved_batch_file: Path = scanner_manager.acquire_with_config(configuration)
            batch_size_megabytes: float = float(saved_batch_file.stat().st_size) / (1024.0 * 1024.0)
            print(f"[Success] Saved: {saved_batch_file.name} ({batch_size_megabytes:.2f} MB)")

            if configuration.max_scans > 0 and iteration_number >= configuration.max_scans:
                print(f"\n[Done] Reached configured --max-scans={configuration.max_scans}.")
                break

            display_countdown(interval_int, action_description="Next scan starts in")
            iteration_number += 1
    except KeyboardInterrupt:
        print("\n[Stopped] Scanning loop terminated by user.")


def handle_card_command(
    scanner_manager: ScannerManager,
    arguments: argparse.Namespace,
) -> None:
    """
    Execute the ID-1 card capture, contour deskewing, and corner masking workflow.

    Parameters
    ----------
    scanner_manager : ScannerManager
        Initialized hardware scanner manager.
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    base_directory: Path = Path(str(getattr(arguments, "output_directory", r"D:\Pictures\Scanned")))
    cards_directory: Path = base_directory / "cards"
    cards_directory.mkdir(parents=True, exist_ok=True)

    card_resolution_dpi: int = int(arguments.card_resolution_dpi)
    output_extension: str = (
        "jpg"
        if str(arguments.output_format).lower() in ("jpg", "jpeg")
        else str(arguments.output_format).lower()
    )
    usb_only_flag: bool = bool(getattr(arguments, "usb_only", False))
    requested_backend: str = str(getattr(arguments, "backend_mode", "auto"))
    effective_backend: str = "wia" if (usb_only_flag and requested_backend == "auto") else requested_backend

    print("--------------------------------------------------")
    print("  white-pepper: ID-1 Card Acquisition Active")
    print("  Region     : 5.0\" x 5.0\" Platen Corner (id-card)")
    print(f"  Resolution : {card_resolution_dpi} DPI ({arguments.color_mode})")
    print(f"  Destination: {cards_directory}")
    print("--------------------------------------------------\n")

    if not bool(arguments.skip_prompt):
        wait_for_spacebar("Place card against top-left platen corner. Press SPACEBAR to scan...")

    temporary_raw_capture_path: Path = scanner_manager.generate_filepath(
        prefix="raw_card",
        extension="png",
        resolution_dpi=card_resolution_dpi,
        paper_size="id-card",
        target_directory=cards_directory,
    )

    raw_capture_configuration: ScanConfiguration = ScanConfiguration(
        destination_directory=cards_directory,
        output_file_path=temporary_raw_capture_path,
        paper_size="id-card",
        resolution_dpi=card_resolution_dpi,
        maximum_quality=(card_resolution_dpi == 1200),
        color_mode=str(arguments.color_mode),
        intent_type="photo",
        output_format="png",
        enable_beep=not bool(getattr(arguments, "disable_beep", False)),
        prefer_escl=(not usb_only_flag) and (effective_backend in ("auto", "escl")),
        backend_mode=effective_backend,
        escl_host=str(getattr(arguments, "escl_ip", DEFAULT_ESCL_IP)),
        escl_port=int(getattr(arguments, "escl_port", DEFAULT_ESCL_PORT)),
    )

    print("Acquiring 5x5 inch platen area...")
    saved_raw_path: Path = scanner_manager.acquire_with_config(
        configuration=raw_capture_configuration,
        output_file_path=temporary_raw_capture_path,
    )

    if bool(arguments.skip_deskew):
        print(f"[Success] Raw card capture saved: {saved_raw_path}")
        return

    print("Running computer vision contour detection and edge pinning...")
    raw_bgr_image: Optional[np.ndarray] = cv2.imread(str(saved_raw_path), cv2.IMREAD_COLOR)
    if raw_bgr_image is None:
        print("[Warning] Could not read raw card image for deskewing.")
        return

    extraction_result: Optional[CardExtractionResult] = extract_and_deskew_id_card(
        raw_bgr_image,
        resolution_dpi=card_resolution_dpi,
        safety_inset_millimeters=float(arguments.safety_inset_mm),
        corner_radius_millimeters=float(arguments.corner_radius_mm),
    )

    if extraction_result is None:
        print("[Warning] Could not isolate card contour automatically. Keeping raw capture.")
        return

    card_filename_prefix: str = str(getattr(arguments, "card_filename_prefix", "card")).strip() or "card"
    final_card_path: Path = cards_directory / f"{card_filename_prefix}_{saved_raw_path.stem}.{output_extension}"
    requested_background: str = str(arguments.background_mode)
    effective_background: str = (
        "white"
        if (output_extension in ("jpg", "bmp") and requested_background == "transparent")
        else requested_background
    )
    composited_image: np.ndarray = composite_card_onto_background(
        extraction_result.extracted_image,
        background_mode=effective_background,
    )

    if (
        len(composited_image.shape) == 3
        and composited_image.shape[2] == 4
        and output_extension in ("png", "tiff")
    ):
        bgra_to_rgba: np.ndarray = cv2.cvtColor(composited_image, cv2.COLOR_BGRA2RGBA)
        pil_rgba_card: Image.Image = Image.fromarray(bgra_to_rgba)
        pil_format_name: str = "TIFF" if output_extension == "tiff" else "PNG"
        pil_rgba_card.save(
            str(final_card_path),
            format=pil_format_name,
            dpi=(float(card_resolution_dpi), float(card_resolution_dpi)),
        )
    else:
        bgr_card: np.ndarray = (
            composited_image[:, :, :3]
            if (len(composited_image.shape) == 3 and composited_image.shape[2] == 4)
            else composited_image
        )
        apply_post_scan_adjustments_and_save(
            source_bgr_image=bgr_card,
            output_file_path=final_card_path,
            resolution_dpi=card_resolution_dpi,
            color_mode=str(arguments.color_mode),
            output_format=output_extension,
            jpeg_quality=int(arguments.jpeg_quality),
        )

    if saved_raw_path.exists() and saved_raw_path != final_card_path:
        saved_raw_path.unlink()

    print(
        f"[Success] Extracted ID-1 Card: {final_card_path} "
        f"({extraction_result.target_width_pixels}x{extraction_result.target_height_pixels} px, "
        f"Deskew angle: {extraction_result.rotation_angle_degrees:.2f} deg, "
        f"Confidence: {extraction_result.confidence_score * 100.0:.1f}%)"
    )


def handle_booklet_command(
    scanner_manager: ScannerManager,
    arguments: argparse.Namespace,
) -> None:
    """
    Execute the continuous booklet spread capture workflow.

    Parameters
    ----------
    scanner_manager : ScannerManager
        Initialized hardware scanner manager.
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    base_directory: Path = Path(str(getattr(arguments, "output_directory", r"D:\Pictures\Scanned")))
    booklet_directory: Path = base_directory / "dairy_scans"
    booklet_directory.mkdir(parents=True, exist_ok=True)

    interval_delay_seconds: int = max(1, int(arguments.booklet_interval_seconds))
    start_delay_seconds: int = max(0, int(arguments.start_delay_seconds))
    maximum_spreads_count: int = max(0, int(arguments.max_scans))
    spread_resolution_dpi: int = int(arguments.resolution_dpi)
    spread_extension: str = (
        "jpg"
        if str(arguments.output_format).lower() == "jpeg"
        else str(arguments.output_format).lower()
    )

    usb_only_flag: bool = bool(getattr(arguments, "usb_only", False))
    requested_backend: str = str(getattr(arguments, "backend_mode", "auto"))
    effective_backend: str = "wia" if (usb_only_flag and requested_backend == "auto") else requested_backend

    booklet_scan_config: ScanConfiguration = ScanConfiguration(
        destination_directory=booklet_directory,
        paper_size=str(arguments.paper_size),
        resolution_dpi=spread_resolution_dpi,
        maximum_quality=(spread_resolution_dpi == 1200),
        color_mode=str(arguments.color_mode),
        output_format=spread_extension,
        enable_beep=not bool(getattr(arguments, "disable_beep", False)),
        prefer_escl=(not usb_only_flag) and (effective_backend in ("auto", "escl")),
        backend_mode=effective_backend,
        escl_host=str(getattr(arguments, "escl_ip", DEFAULT_ESCL_IP)),
        escl_port=int(getattr(arguments, "escl_port", DEFAULT_ESCL_PORT)),
        max_scans=maximum_spreads_count,
        interval_seconds=float(interval_delay_seconds),
        start_delay_seconds=float(start_delay_seconds),
    )

    print("--------------------------------------------------")
    print("  white-pepper: Booklet Spread Capture Active")
    print(f"  Paper Size : {booklet_scan_config.paper_size} @ {spread_resolution_dpi} DPI ({booklet_scan_config.color_mode})")
    print(f"  Interval   : {interval_delay_seconds} seconds")
    print(f"  Destination: {booklet_directory}")
    print("--------------------------------------------------\n")

    if start_delay_seconds > 0:
        display_countdown(start_delay_seconds, action_description="First spread capture starts in")

    page_counter: int = 1
    try:
        while True:
            target_path: Path = booklet_directory / f"{page_counter:02d}.{spread_extension}"
            print(f"[Capturing Spread #{page_counter}]")
            scanner_manager.acquire_with_config(
                configuration=booklet_scan_config,
                output_file_path=target_path,
            )
            print(f"[Saved] {target_path.name}")
            if maximum_spreads_count > 0 and page_counter >= maximum_spreads_count:
                print(f"\n[Done] Captured configured --max-scans={maximum_spreads_count} spreads.")
                break
            display_countdown(interval_delay_seconds, action_description="Turn page. Next capture in")
            page_counter += 1
    except KeyboardInterrupt:
        print("\n[Stopped] Booklet scanning loop terminated by user.")


def handle_legal_stitch_command(
    scanner_manager: ScannerManager,
    arguments: argparse.Namespace,
) -> None:
    """Execute the two-pass zero-gradient US Legal scanning and stitching workflow.

    Parameters
    ----------
    scanner_manager : ScannerManager
        Initialized White Pepper hardware controller.
    arguments : argparse.Namespace
        Parsed CLI arguments for the legal-stitch command.

    Returns
    -------
    None
    """
    base_directory: Path = Path(str(getattr(arguments, "output_directory", r"D:\Pictures\Scanned")))
    legal_directory: Path = base_directory / "legal"
    legal_directory.mkdir(parents=True, exist_ok=True)

    resolution_dpi: int = int(arguments.resolution_dpi)
    document_name: str = str(arguments.document_name).strip("\"'")
    color_mode: str = str(arguments.color_mode)
    output_format: str = str(arguments.output_format).lower()
    enable_ipc_mode: bool = bool(arguments.enable_ipc_mode)
    usb_only_flag: bool = bool(getattr(arguments, "usb_only", False))
    requested_backend: str = str(getattr(arguments, "backend_mode", "auto"))
    effective_backend: str = "wia" if (usb_only_flag and requested_backend == "auto") else requested_backend
    prefer_escl_flag: bool = (not usb_only_flag) and (effective_backend in ("auto", "escl"))

    temporary_scratch_directory: Path = legal_directory / "_scratch_legal"
    temporary_scratch_directory.mkdir(parents=True, exist_ok=True)

    target_output_path: Path = legal_directory / f"{document_name}.{output_format}"

    if not enable_ipc_mode:
        print("--------------------------------------------------")
        print("  white-pepper: US Legal (8.5\" x 14.0\") 2-Pass Stitching")
        print("  Strategy   : Dual Letter Clamped (Zero Black Gradient)")
        print(f"  Resolution : {resolution_dpi} DPI ({color_mode})")
        print(f"  Destination: {target_output_path}")
        print("--------------------------------------------------\n")

    try:
        # Pass 1: Upright Top Scan
        if enable_ipc_mode:
            print('{"event": "step_prompt", "step": 1, "message": "Place Legal paper upright at top-left printer markings."}', flush=True)
            sys.stdin.readline()
        else:
            wait_for_spacebar("[STEP 1 OF 2] Place Legal paper UPRIGHT at top-left markings. Press SPACEBAR to scan Pass 1...")

        pass1_temporary_path: Path = temporary_scratch_directory / "pass1_top.png"
        pass1_configuration: ScanConfiguration = ScanConfiguration(
            destination_directory=temporary_scratch_directory,
            output_file_path=pass1_temporary_path,
            paper_size="letter",
            resolution_dpi=resolution_dpi,
            maximum_quality=(resolution_dpi == 1200),
            color_mode=color_mode,
            intent_type="document",
            output_format="png",
            enable_beep=not bool(getattr(arguments, "disable_beep", False)),
            prefer_escl=prefer_escl_flag,
            backend_mode=effective_backend,
            escl_host=str(getattr(arguments, "escl_ip", DEFAULT_ESCL_IP)),
            escl_port=int(getattr(arguments, "escl_port", DEFAULT_ESCL_PORT)),
        )

        if not enable_ipc_mode:
            print("Acquiring Pass 1 (Top Letter Region)...")
        scanner_manager.acquire_with_config(
            configuration=pass1_configuration,
            output_file_path=pass1_temporary_path,
        )

        # Pass 2: Upside-Down Bottom Scan
        if enable_ipc_mode:
            print('{"event": "step_prompt", "step": 2, "message": "Rotate paper 180° upside-down. Align opposite corner at markings."}', flush=True)
            sys.stdin.readline()
        else:
            wait_for_spacebar("\n[STEP 2 OF 2] Rotate paper 180° UPSIDE-DOWN. Align opposite corner at markings. Press SPACEBAR to scan Pass 2...")

        pass2_temporary_path: Path = temporary_scratch_directory / "pass2_bottom.png"
        pass2_configuration: ScanConfiguration = ScanConfiguration(
            destination_directory=temporary_scratch_directory,
            output_file_path=pass2_temporary_path,
            paper_size="letter",
            resolution_dpi=resolution_dpi,
            maximum_quality=(resolution_dpi == 1200),
            color_mode=color_mode,
            intent_type="document",
            output_format="png",
            enable_beep=not bool(getattr(arguments, "disable_beep", False)),
            prefer_escl=prefer_escl_flag,
            backend_mode=effective_backend,
            escl_host=str(getattr(arguments, "escl_ip", DEFAULT_ESCL_IP)),
            escl_port=int(getattr(arguments, "escl_port", DEFAULT_ESCL_PORT)),
        )

        if not enable_ipc_mode:
            print("Acquiring Pass 2 (Bottom Letter Region)...")
        scanner_manager.acquire_with_config(
            configuration=pass2_configuration,
            output_file_path=pass2_temporary_path,
        )

        # Stitching
        if enable_ipc_mode:
            print('{"event": "stitching", "message": "Joining scans via Fourier phase-correlation registration..."}', flush=True)
        else:
            print("\nStitching two passes into seamless 8.5\" x 14.0\" legal document...")

        pass1_bgr_image: Optional[np.ndarray] = cv2.imread(str(pass1_temporary_path), cv2.IMREAD_COLOR)
        pass2_bgr_image: Optional[np.ndarray] = cv2.imread(str(pass2_temporary_path), cv2.IMREAD_COLOR)

        if pass1_bgr_image is None or pass2_bgr_image is None:
            raise RuntimeError("Failed to read acquired pass images for stitching.")

        stitch_result: LegalStitchResult = stitch_legal_two_pass(
            pass1_top_bgr_image=pass1_bgr_image,
            pass2_bottom_upside_down_bgr_image=pass2_bgr_image,
            resolution_dpi=resolution_dpi,
            enable_phase_correlation=True,
        )

        if output_format == "pdf":
            save_legal_stitch_result_to_pdf(stitch_result, target_output_path)
        else:
            rgb_composite: np.ndarray = cv2.cvtColor(stitch_result.stitched_bgr_image, cv2.COLOR_BGR2RGB)
            pil_composite: Image.Image = Image.fromarray(rgb_composite)
            pil_composite.save(target_output_path, "PNG", dpi=(float(resolution_dpi), float(resolution_dpi)))

        # Clean up scratch files
        if pass1_temporary_path.exists():
            pass1_temporary_path.unlink()
        if pass2_temporary_path.exists():
            pass2_temporary_path.unlink()
        if temporary_scratch_directory.exists() and not any(temporary_scratch_directory.iterdir()):
            temporary_scratch_directory.rmdir()

        if enable_ipc_mode:
            completed_payload: str = json.dumps(
                {"event": "completed", "output_path": str(target_output_path)}
            )
            print(completed_payload, flush=True)
        else:
            print(
                f"[Success] Stitched US Legal Document: {target_output_path} "
                f"({stitch_result.stitched_bgr_image.shape[1]}x{stitch_result.stitched_bgr_image.shape[0]} px @ {resolution_dpi} DPI, "
                f"Registration confidence: {stitch_result.correlation_confidence * 100.0:.1f}%)"
            )
    except Exception as acquisition_error:
        if enable_ipc_mode:
            error_payload: str = json.dumps(
                {"event": "error", "message": str(acquisition_error)}
            )
            print(error_payload, flush=True)
        else:
            print(f"[Error] Legal two-pass stitching failed: {acquisition_error}", file=sys.stderr)


def main() -> None:
    """
    Main CLI entry point for ``scan_cli``.

    Returns
    -------
    None
    """
    parser: argparse.ArgumentParser = build_argument_parser()
    arguments: argparse.Namespace = parser.parse_args()

    if arguments.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        if arguments.command == "flatbed":
            resolve_flatbed_scan_configuration(arguments)
    except ValueError as validation_error:
        parser.error(str(validation_error))

    scanner_manager: ScannerManager = ScannerManager(
        destination_directory=Path(str(arguments.output_directory)),
        escl_host=str(arguments.escl_ip),
        escl_port=int(arguments.escl_port),
    )

    if arguments.command == "flatbed":
        handle_flatbed_command(scanner_manager, arguments)
    elif arguments.command == "card":
        handle_card_command(scanner_manager, arguments)
    elif arguments.command == "booklet":
        handle_booklet_command(scanner_manager, arguments)
    elif arguments.command == "legal-stitch":
        handle_legal_stitch_command(scanner_manager, arguments)


if __name__ == "__main__":
    main()
