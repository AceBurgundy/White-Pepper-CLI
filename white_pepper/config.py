"""
Strongly-typed configuration contracts for acquisition, vision, and PDF compilation.

All configuration dataclasses in this module are pure-Python, UI-agnostic value
contracts shared between the headless CLI scripts and the PyQt6 desktop interface.
"""

from __future__ import annotations

# eSCL = Enhanced Scanner Client Language
# WIA = Windows Image Acquisition
# DPI = Dots Per Inch
# OCR = Optical Character Recognition
# PDF = Portable Document Format
# ID-1 = Identification Card Format 1 (ISO/IEC 7810)
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format
# HTTP = Hypertext Transfer Protocol
# TCP = Transmission Control Protocol
# XML = Extensible Markup Language
# CLI = Command Line Interface
# UI = User Interface
# LTR = Left to Right
# RTL = Right to Left

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from white_pepper.algorithms.geometry import (
    ID1_CORNER_RADIUS_MILLIMETERS,
    ResolvedScanRegion,
    resolve_scan_region,
)

SUPPORTED_DPI_VALUES: tuple[int, ...] = (75, 100, 200, 300, 600, 1200)
SUPPORTED_COLOR_MODES: tuple[str, ...] = ("color", "grayscale", "bw")
SUPPORTED_SCAN_INTENTS: tuple[str, ...] = ("document", "photo", "text-and-graphic", "preview")
SUPPORTED_IMAGE_FORMATS: tuple[str, ...] = ("png", "jpg", "jpeg", "tiff", "bmp", "pdf")
SUPPORTED_BACKEND_MODES: tuple[str, ...] = ("auto", "escl", "wia", "powershell")
SUPPORTED_ROTATION_ANGLES: tuple[int, ...] = (0, 90, 180, 270)
SUPPORTED_PDF_FIT_MODES: tuple[str, ...] = ("contain", "fill", "stretch", "original")
SUPPORTED_CARD_BACKGROUNDS: tuple[str, ...] = ("transparent", "white", "black")

ESCL_INTENT_MAPPING: dict[str, str] = {
    "document": "Document",
    "photo": "Photo",
    "text-and-graphic": "TextAndGraphic",
    "textandgraphic": "TextAndGraphic",
    "preview": "Preview",
}

ESCL_COLOR_MODE_MAPPING: dict[str, str] = {
    "color": "RGB24",
    "grayscale": "Grayscale8",
    "bw": "BlackAndWhite1",
}


@dataclass
class ScanConfiguration:
    """
    Comprehensive parameter contract for a single or continuous flatbed scan session.

    Attributes
    ----------
    destination_directory : Path
        Base directory where output scans are written.
    subfolder_name : Optional[str]
        Optional subdirectory created beneath ``destination_directory``.
    output_file_path : Optional[Path]
        Explicit output file path for single-scan overrides, or ``None`` for auto-naming.
    filename_prefix : str
        Filename prefix used when generating timestamped output paths.
    paper_size : str
        Standard paper size key from ``PAPER_SIZE_REGISTRY`` or ``"custom"``.
    area_mode : str
        Legacy area modifier (``"full"``, ``"half"``, or ``"quarter-tl"``).
    page_orientation : str
        Page orientation (``"portrait"`` or ``"landscape"``).
    custom_width : Optional[float]
        Explicit scan width in ``measurement_unit`` when ``paper_size == "custom"``.
    custom_height : Optional[float]
        Explicit scan height in ``measurement_unit`` when ``paper_size == "custom"``.
    offset_x : float
        Horizontal origin offset from top-left platen corner in ``measurement_unit``.
    offset_y : float
        Vertical origin offset from top-left platen corner in ``measurement_unit``.
    measurement_unit : str
        Dimensional unit for custom geometry and offsets (``"mm"`` or ``"in"``).
    resolution_dpi : int
        Discrete optical resolution in dots per inch (``75`` to ``1200``).
    maximum_quality : bool
        Legacy toggle promoting optical resolution to ``1200`` DPI when ``True``.
    color_mode : str
        Channel mode (``"color"``, ``"grayscale"``, or ``"bw"``).
    intent_type : str
        Hardware scan intent (``"document"``, ``"photo"``, ``"text-and-graphic"``, ``"preview"``).
    output_format : str
        Encoded file extension (``"png"``, ``"jpg"``, ``"jpeg"``, ``"tiff"``, ``"bmp"``, ``"pdf"``).
    jpeg_quality : int
        JPEG encoding quality factor in ``[1, 100]``.
    brightness : int
        Relative brightness adjustment in ``[-100, 100]`` (``0`` is neutral).
    contrast : int
        Relative contrast adjustment in ``[-100, 100]`` (``0`` is neutral).
    rotation_degrees : int
        Clockwise post-scan rotation angle in ``{0, 90, 180, 270}``.
    auto_crop_whitespace : bool
        Automatically trim uniform white/light borders around scanned content when ``True``.
    interval_seconds : Optional[float]
        Pause duration in seconds between consecutive batch scans, or ``None`` for single scan.
    max_scans : int
        Maximum number of scans to capture during a continuous session (``0`` = unlimited).
    start_delay_seconds : float
        Initial countdown delay in seconds before the first scan begins.
    enable_beep : bool
        Emit an audible completion tone after each acquired scan when ``True``.
    prefer_escl : bool
        Prefer wireless eSCL acquisition when ``backend_mode == "auto"``.
    backend_mode : str
        Transport selection strategy (``"auto"``, ``"escl"``, ``"wia"``, ``"powershell"``).
    escl_host : str
        IPv4 address or hostname of the wireless eSCL scanner.
    escl_port : int
        TCP port of the wireless eSCL scanner HTTP endpoint.
    """

    destination_directory: Path = Path(r"D:\Pictures\Scanned")
    subfolder_name: Optional[str] = None
    output_file_path: Optional[Path] = None
    filename_prefix: str = "scan"
    paper_size: str = "full"
    area_mode: str = "full"
    page_orientation: str = "portrait"
    custom_width: Optional[float] = None
    custom_height: Optional[float] = None
    offset_x: float = 0.0
    offset_y: float = 0.0
    measurement_unit: str = "mm"
    resolution_dpi: int = 300
    maximum_quality: bool = False
    color_mode: str = "color"
    intent_type: str = "document"
    output_format: str = "png"
    jpeg_quality: int = 95
    brightness: int = 0
    contrast: int = 0
    rotation_degrees: int = 0
    auto_crop_whitespace: bool = False
    interval_seconds: Optional[float] = None
    max_scans: int = 1
    start_delay_seconds: float = 0.0
    enable_beep: bool = True
    prefer_escl: bool = True
    backend_mode: str = "auto"
    escl_host: str = "192.168.1.150"
    escl_port: int = 8080

    def effective_dpi(self) -> int:
        """
        Return the effective optical DPI accounting for ``maximum_quality``.

        Returns
        -------
        int
            Optical scan resolution in dots per inch.
        """
        resolved_dpi: int = 1200 if self.maximum_quality else self.resolution_dpi
        return resolved_dpi

    def normalized_extension(self) -> str:
        """
        Return the canonical lowercase file extension without a leading dot.

        Returns
        -------
        str
            Normalized file extension (e.g., ``"png"``, ``"jpg"``, ``"tiff"``, ``"bmp"``, ``"pdf"``).

        Raises
        ------
        ValueError
            If ``output_format`` is not in ``SUPPORTED_IMAGE_FORMATS``.
        """
        cleaned_format: str = self.output_format.strip().lower().lstrip(".")
        if cleaned_format not in SUPPORTED_IMAGE_FORMATS:
            supported_list: str = ", ".join(SUPPORTED_IMAGE_FORMATS)
            raise ValueError(
                f"Unsupported output format '{self.output_format}'. Expected one of: {supported_list}."
            )
        if cleaned_format == "jpeg":
            return "jpg"
        return cleaned_format

    def escl_intent_name(self) -> str:
        """
        Map ``intent_type`` to the canonical eSCL XML ``<scan:Intent>`` token.

        Returns
        -------
        str
            eSCL protocol intent string (``"Document"``, ``"Photo"``, ``"TextAndGraphic"``, or ``"Preview"``).
        """
        normalized_key: str = self.intent_type.strip().lower()
        mapped_intent: str = ESCL_INTENT_MAPPING.get(normalized_key, "Document")
        return mapped_intent

    def escl_color_mode_name(self) -> str:
        """
        Map ``color_mode`` to the canonical eSCL XML ``<scan:ColorMode>`` token.

        Returns
        -------
        str
            eSCL protocol color mode string (``"RGB24"``, ``"Grayscale8"``, or ``"BlackAndWhite1"``).
        """
        normalized_mode: str = self.color_mode.strip().lower()
        mapped_color: str = ESCL_COLOR_MODE_MAPPING.get(normalized_mode, "RGB24")
        return mapped_color

    def target_directory(self) -> Path:
        """
        Compute the resolved output directory including any configured ``subfolder_name``.

        Returns
        -------
        Path
            Target filesystem directory for saved scan files.
        """
        if self.subfolder_name and self.subfolder_name.strip():
            resolved_folder: Path = self.destination_directory / self.subfolder_name.strip()
            return resolved_folder
        return self.destination_directory

    def resolve_region(self) -> ResolvedScanRegion:
        """
        Resolve and validate the physical scan region for this configuration.

        Returns
        -------
        ResolvedScanRegion
            Clamped flatbed scan region in millimeters, inches, points, and eSCL units.
        """
        region: ResolvedScanRegion = resolve_scan_region(
            paper_size=self.paper_size,
            area_mode=self.area_mode,
            page_orientation=self.page_orientation,
            custom_width=self.custom_width,
            custom_height=self.custom_height,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            measurement_unit=self.measurement_unit,
        )
        return region


@dataclass
class CardProcessConfiguration:
    """
    Parameter contract for ID-1 card contour extraction, deskewing, and compositing.

    Attributes
    ----------
    input_directory : Path
        Source image file or directory containing raw card scans.
    output_directory : Path
        Destination directory where extracted card images are saved.
    resolution_dpi : int
        Source scan resolution in dots per inch used for millimeter scaling.
    safety_inset_millimeters : float
        Edge inset margin in millimeters applied during extraction.
    corner_radius_millimeters : float
        Rounded corner mask radius in millimeters (``3.18`` mm for ISO/IEC 7810 ID-1).
    background_mode : str
        Compositing background style (``"transparent"``, ``"white"``, or ``"black"``).
    output_format : str
        Output file format (``"png"`` or ``"jpg"``).
    jpeg_quality : int
        JPEG quality factor ``[1, 100]`` when saving as ``"jpg"``.
    """

    input_directory: Path
    output_directory: Path
    resolution_dpi: int = 300
    safety_inset_millimeters: float = 0.5
    corner_radius_millimeters: float = ID1_CORNER_RADIUS_MILLIMETERS
    background_mode: str = "transparent"
    output_format: str = "png"
    jpeg_quality: int = 95


@dataclass
class BookletProcessConfiguration:
    """
    Parameter contract for dual-page booklet spread splitting and optional PDF export.

    Attributes
    ----------
    input_directory : Path
        Source directory containing raw booklet spread images.
    output_directory : Path
        Destination directory where split and upright-oriented pages are written.
    split_dual_pages : bool
        Split two-page spreads into individual left/right pages when ``True``.
    enable_ocr_orientation : bool
        Automatically detect and rotate upside-down or sideways pages via OCR when ``True``.
    spread_orientation : str
        Spread layout hint (``"auto"``, ``"landscape"``, or ``"portrait"``).
    reading_direction : str
        Page ordering direction (``"ltr"`` for left-to-right or ``"rtl"`` for right-to-left).
    spread_aspect_ratio_threshold : float
        Minimum width-to-height ratio treated as a dual-page spread in ``"auto"`` mode.
    rotate_even_spreads_180 : bool
        Pre-rotate every second raw spread by 180 degrees before segmentation when ``True``.
    margin_padding_pixels : int
        Pixel margin retained around detected page contours.
    output_format : str
        Output image format for segmented pages (``"png"`` or ``"jpg"``).
    jpeg_quality : int
        JPEG compression quality ``[1, 100]`` when ``output_format == "jpg"``.
    compile_pdf_path : Optional[Path]
        Optional destination PDF path to compile segmented pages directly after splitting.
    pdf_paper_size : str
        Target PDF page size key when ``compile_pdf_path`` is set (e.g., ``"auto"``, ``"a4"``).
    pdf_margin_millimeters : float
        Target PDF page margin in millimeters when ``compile_pdf_path`` is set.
    resolution_dpi : int
        Target resolution in dots per inch for PDF compilation.
    """

    input_directory: Path
    output_directory: Path
    split_dual_pages: bool = True
    enable_ocr_orientation: bool = True
    spread_orientation: str = "auto"
    reading_direction: str = "ltr"
    spread_aspect_ratio_threshold: float = 1.2
    rotate_even_spreads_180: bool = False
    margin_padding_pixels: int = 15
    output_format: str = "png"
    jpeg_quality: int = 95
    compile_pdf_path: Optional[Path] = None
    pdf_paper_size: str = "auto"
    pdf_margin_millimeters: float = 0.0
    resolution_dpi: int = 300


@dataclass
class PdfCompilationConfiguration:
    """
    Parameter contract for multi-image PDF document layout, fitting, and metadata.

    Attributes
    ----------
    input_directory : Optional[Path]
        Directory scanned in natural sort order when ``input_image_paths`` is not supplied.
    output_pdf_path : Path
        Target file path for the compiled PDF document.
    input_image_paths : Optional[list[Path]]
        Explicit ordered list of image files to compile, overriding ``input_directory``.
    paper_size : str
        Target virtual page size (``"auto"``, any ``PAPER_SIZE_REGISTRY`` key, or ``"custom"``).
    page_orientation : str
        Virtual page orientation (``"auto"``, ``"portrait"``, or ``"landscape"``).
    custom_width_millimeters : Optional[float]
        Custom page width in millimeters when ``paper_size == "custom"``.
    custom_height_millimeters : Optional[float]
        Custom page height in millimeters when ``paper_size == "custom"``.
    margin_millimeters : float
        Uniform page margin inset in millimeters around placed images.
    fit_mode : str
        Image placement strategy (``"contain"``, ``"fill"``, ``"stretch"``, or ``"original"``).
    resolution_dpi : int
        Reference raster resolution in dots per inch for ``"auto"`` and ``"original"`` sizing.
    jpeg_compression_quality : int
        Optional JPEG stream recompression quality in ``[1, 100]`` (``100`` preserves lossless PNG).
    document_title : str
        PDF metadata ``Title`` string.
    document_author : str
        PDF metadata ``Author`` string.
    """

    input_directory: Optional[Path] = None
    output_pdf_path: Path = Path("compiled_output.pdf")
    input_image_paths: Optional[list[Path]] = None
    paper_size: str = "auto"
    page_orientation: str = "auto"
    custom_width_millimeters: Optional[float] = None
    custom_height_millimeters: Optional[float] = None
    margin_millimeters: float = 0.0
    fit_mode: str = "contain"
    resolution_dpi: int = 300
    jpeg_compression_quality: int = 92
    document_title: str = ""
    document_author: str = ""
