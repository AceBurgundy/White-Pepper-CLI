"""
Centralized Document & Image Processing CLI.

Provides command-line interfaces for post-scan computer vision operations,
ID-1 card deskewing and background compositing, booklet dual-page splitting
and OCR upright rotation, and multi-format virtual-paper PDF compilation.
"""

from __future__ import annotations
from PIL import Image

# CLI = Command Line Interface
# DPI = Dots Per Inch
# OCR = Optical Character Recognition
# PDF = Portable Document Format
# ID-1 = Identification Card Format 1 (ISO/IEC 7810)
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format
# LTR = Left to Right
# RTL = Right to Left

import argparse
from pathlib import Path
import sys
from typing import Optional

import cv2
import numpy as np

from white_pepper.algorithms.booklet_vision import (
    BookletPageSegment,
    segment_booklet_with_config,
)
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
    PAPER_SIZE_REGISTRY,
)
from white_pepper.algorithms.ocr_orientation import (
    detect_upright_orientation_angle,
    rotate_image_to_upright,
)
from white_pepper.config import (
    SUPPORTED_CARD_BACKGROUNDS,
    SUPPORTED_PDF_FIT_MODES,
    BookletProcessConfiguration,
    PdfCompilationConfiguration,
)
from white_pepper.document.pdf_builder import (
    compile_pdf_with_config,
    discover_image_sequence,
)
from white_pepper.hardware.escl_client import apply_post_scan_adjustments_and_save

PDF_PAPER_CHOICES: list[str] = ["auto"] + list(PAPER_SIZE_REGISTRY.keys()) + ["custom"]


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Construct the command-line argument parser for ``process_cli``.

    Returns
    -------
    argparse.ArgumentParser
        Configured root parser with ``cards``, ``booklets``, and ``compile-pdf`` subcommands.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="process_cli",
        description="Unified Document Vision & PDF Compilation CLI for white-pepper.",
        add_help=True,
    )

    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command",
        help="Processing command to execute.",
    )

    card_parser: argparse.ArgumentParser = subparsers.add_parser(
        "cards",
        aliases=["card"],
        help="Batch or single-file deskew, edge-pin, and mask raw card scans.",
    )
    card_parser.add_argument(
        "--input-dir",
        "--input",
        dest="input_directory",
        type=str,
        required=True,
        help="Input directory or single raw card image path.",
    )
    card_parser.add_argument(
        "--output-dir",
        dest="output_directory",
        type=str,
        required=True,
        help="Directory where extracted ID-1 cards will be saved.",
    )
    card_parser.add_argument(
        "--resolution",
        "--dpi",
        dest="resolution_dpi",
        type=int,
        default=300,
        help="DPI resolution of source scans (default: 300).",
    )
    card_parser.add_argument(
        "--safety-inset-mm",
        "--padding",
        dest="safety_inset_mm",
        type=float,
        default=0.5,
        help="Edge safety inset in millimeters trimmed during deskew (default: 0.5).",
    )
    card_parser.add_argument(
        "--corner-radius-mm",
        "--corner-radius",
        dest="corner_radius_mm",
        type=float,
        default=ID1_CORNER_RADIUS_MILLIMETERS,
        help="Rounded corner mask radius in millimeters (default: 3.18).",
    )
    card_parser.add_argument(
        "--background",
        dest="background_mode",
        choices=list(SUPPORTED_CARD_BACKGROUNDS),
        default="transparent",
        help="Corner background compositing mode: transparent, white, or black (default: transparent).",
    )
    card_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["png", "jpg", "jpeg", "tiff", "bmp"],
        default="png",
        help="Output image format for extracted cards (default: png).",
    )
    card_parser.add_argument(
        "--jpeg-quality",
        dest="jpeg_quality",
        type=int,
        default=95,
        help="JPEG encoding quality from 1 to 100 when saving as jpg (default: 95).",
    )

    booklet_parser: argparse.ArgumentParser = subparsers.add_parser(
        "booklets",
        aliases=["booklet"],
        help="Batch segment booklet spreads, split dual pages, orient via OCR, and optionally compile PDF.",
    )
    booklet_parser.add_argument(
        "--input-dir",
        dest="input_directory",
        type=str,
        required=True,
        help="Directory containing booklet spread images.",
    )
    booklet_parser.add_argument(
        "--output-dir",
        dest="output_directory",
        type=str,
        required=True,
        help="Directory where isolated, upright pages will be saved.",
    )
    booklet_parser.add_argument(
        "--single-page",
        dest="single_page",
        action="store_true",
        default=False,
        help="Keep full spreads intact without dual-page left/right splitting.",
    )
    booklet_parser.add_argument(
        "--no-ocr",
        dest="skip_ocr",
        action="store_true",
        default=False,
        help="Skip RapidOCR upright text orientation detection.",
    )
    booklet_parser.add_argument(
        "--orientation",
        dest="spread_orientation",
        choices=["auto", "landscape", "portrait"],
        default="landscape",
        help="Spread orientation rule: landscape (always split), portrait (single), or auto (aspect threshold).",
    )
    booklet_parser.add_argument(
        "--reading-direction",
        dest="reading_direction",
        choices=["ltr", "rtl"],
        default="ltr",
        help="Page reading order: ltr (left-to-right) or rtl (right-to-left, default: ltr).",
    )
    booklet_parser.add_argument(
        "--spread-threshold",
        dest="spread_threshold",
        type=float,
        default=1.2,
        help="Minimum width/height ratio treated as a two-page spread when --orientation=auto (default: 1.2).",
    )
    booklet_parser.add_argument(
        "--rotate-even-180",
        dest="rotate_even_180",
        action="store_true",
        default=False,
        help="Rotate even-numbered spreads by 180 degrees prior to splitting.",
    )
    booklet_parser.add_argument(
        "--no-rotate-even-180",
        dest="rotate_even_180",
        action="store_false",
        help="Do not pre-rotate even-numbered spreads (default).",
    )
    booklet_parser.add_argument(
        "--margin-padding-px",
        dest="margin_padding_px",
        type=int,
        default=15,
        help="Contour padding margin in pixels retained around segmented pages (default: 15).",
    )
    booklet_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["png", "jpg", "jpeg", "tiff", "bmp"],
        default="png",
        help="Output image format for segmented booklet pages (default: png).",
    )
    booklet_parser.add_argument(
        "--jpeg-quality",
        dest="jpeg_quality",
        type=int,
        default=95,
        help="JPEG encoding quality from 1 to 100 when saving as jpg (default: 95).",
    )
    booklet_parser.add_argument(
        "--compile-pdf",
        "--pdf-output",
        dest="compile_pdf_path",
        type=str,
        default=None,
        help="Optional PDF filepath to compile all segmented booklet pages immediately.",
    )
    booklet_parser.add_argument(
        "--pdf-paper-size",
        dest="pdf_paper_size",
        choices=PDF_PAPER_CHOICES,
        default="auto",
        help="Target PDF page size when --compile-pdf is used (default: auto).",
    )
    booklet_parser.add_argument(
        "--pdf-margin-mm",
        dest="pdf_margin_mm",
        type=float,
        default=0.0,
        help="Page margin in millimeters when --compile-pdf is used (default: 0.0).",
    )
    booklet_parser.add_argument(
        "--dpi",
        "--resolution",
        dest="resolution_dpi",
        type=int,
        default=300,
        help="Reference DPI for optional PDF compilation (default: 300).",
    )

    pdf_parser: argparse.ArgumentParser = subparsers.add_parser(
        "compile-pdf",
        help="Compile an ordered sequence of images into a layout-controlled PDF document.",
    )
    pdf_parser.add_argument(
        "--input-dir",
        "--input",
        dest="input_directory",
        type=str,
        required=True,
        help="Input directory or image file path(s) (comma-separated when passing multiple files).",
    )
    pdf_parser.add_argument(
        "--output-file",
        "--output",
        dest="output_file_path",
        type=str,
        required=True,
        help="Destination path for the compiled PDF document.",
    )
    pdf_parser.add_argument(
        "--paper-size",
        dest="paper_size",
        choices=PDF_PAPER_CHOICES,
        default="auto",
        help="Virtual PDF paper size: auto, a4, letter, legal, a5, b5, photo-4x6, photo-5x7, custom, etc.",
    )
    pdf_parser.add_argument(
        "--page-orientation",
        dest="page_orientation",
        choices=["auto", "portrait", "landscape"],
        default="auto",
        help="Virtual PDF page orientation: auto, portrait, or landscape (default: auto).",
    )
    pdf_parser.add_argument(
        "--width-mm",
        dest="custom_width_mm",
        type=float,
        default=None,
        help="Custom PDF page width in millimeters when --paper-size=custom.",
    )
    pdf_parser.add_argument(
        "--height-mm",
        dest="custom_height_mm",
        type=float,
        default=None,
        help="Custom PDF page height in millimeters when --paper-size=custom.",
    )
    pdf_parser.add_argument(
        "--margin-mm",
        dest="margin_mm",
        type=float,
        default=0.0,
        help="Uniform page margin inset in millimeters on all four sides (default: 0.0).",
    )
    pdf_parser.add_argument(
        "--fit-mode",
        dest="fit_mode",
        choices=list(SUPPORTED_PDF_FIT_MODES),
        default="contain",
        help="Image placement mode inside page margins: contain, fill, stretch, or original (default: contain).",
    )
    pdf_parser.add_argument(
        "--resolution",
        "--dpi",
        dest="resolution_dpi",
        type=int,
        default=None,
        help="Explicit DPI override for PDF scaling (default: auto-read embedded image DPI, fallback 300).",
    )
    pdf_parser.add_argument(
        "--jpeg-compression",
        "--jpeg-quality",
        dest="jpeg_compression",
        type=int,
        default=0,
        help="Optional JPEG stream compression quality 1..99 (0 retains lossless PNG streams).",
    )
    pdf_parser.add_argument(
        "--title",
        dest="document_title",
        type=str,
        default="",
        help="Optional PDF Title metadata string.",
    )
    pdf_parser.add_argument(
        "--author",
        dest="document_author",
        type=str,
        default="",
        help="Optional PDF Author metadata string.",
    )

    legal_parser: argparse.ArgumentParser = subparsers.add_parser(
        "stitch-legal",
        aliases=["legal-stitch"],
        help="Stitch top upright and bottom upside-down Letter scans into a seamless Legal document.",
    )
    legal_parser.add_argument(
        "--top",
        dest="top_image_path",
        type=Path,
        required=True,
        help="Path to Pass 1 (top upright) Letter scan.",
    )
    legal_parser.add_argument(
        "--bottom",
        dest="bottom_image_path",
        type=Path,
        required=True,
        help="Path to Pass 2 (bottom upside-down) Letter scan.",
    )
    legal_parser.add_argument(
        "--output",
        "-o",
        dest="output_path",
        type=Path,
        required=True,
        help="Destination output path (PDF or PNG).",
    )
    legal_parser.add_argument(
        "--dpi",
        dest="resolution_dpi",
        type=int,
        default=300,
        help="Optical resolution in DPI (default: 300).",
    )

    return parser


def handle_cards_command(arguments: argparse.Namespace) -> None:
    """
    Execute batch or single-file ID-1 card extraction, deskewing, and compositing.

    Parameters
    ----------
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    input_target: Path = Path(str(arguments.input_directory))
    output_directory: Path = Path(str(arguments.output_directory))
    output_directory.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path]
    if input_target.is_file():
        image_paths = [input_target]
    else:
        image_paths = discover_image_sequence(input_target)

    if not image_paths:
        print(f"[Warning] No image files found in {input_target}.")
        return

    output_extension: str = (
        "jpg"
        if str(arguments.output_format).lower() == "jpeg"
        else str(arguments.output_format).lower()
    )
    requested_background: str = str(arguments.background_mode)
    effective_background: str = (
        "white"
        if (output_extension in ("jpg", "bmp") and requested_background == "transparent")
        else requested_background
    )

    print(f"Discovered {len(image_paths)} image(s) to process.")
    total_images: int = len(image_paths)
    item_index: int
    for item_index in range(total_images):
        image_path: Path = image_paths[item_index]
        display_number: int = item_index + 1
        print(f"[{display_number}/{total_images}] Processing {image_path.name}...")
        source_bgr: Optional[np.ndarray] = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if source_bgr is None:
            print("  -> Could not decode source image.")
            continue

        extraction_result: Optional[CardExtractionResult] = extract_and_deskew_id_card(
            source_bgr,
            resolution_dpi=int(arguments.resolution_dpi),
            safety_inset_millimeters=float(arguments.safety_inset_mm),
            corner_radius_millimeters=float(arguments.corner_radius_mm),
        )
        if extraction_result is None:
            print("  -> Could not detect valid card boundary.")
            continue

        destination_path: Path = output_directory / f"card_{image_path.stem}.{output_extension}"
        composited_card: np.ndarray = composite_card_onto_background(
            extraction_result.extracted_image,
            background_mode=effective_background,
        )

        if (
            len(composited_card.shape) == 3
            and composited_card.shape[2] == 4
            and output_extension in ("png", "tiff")
        ):
            target_card_dpi: int = int(arguments.resolution_dpi)
            bgra_to_rgba: np.ndarray = cv2.cvtColor(composited_card, cv2.COLOR_BGRA2RGBA)
            pil_rgba_card: Image.Image = Image.fromarray(bgra_to_rgba)
            pil_format_name: str = "TIFF" if output_extension == "tiff" else "PNG"
            pil_rgba_card.save(
                str(destination_path),
                format=pil_format_name,
                dpi=(float(target_card_dpi), float(target_card_dpi)),
            )
        else:
            bgr_only: np.ndarray = (
                composited_card[:, :, :3]
                if (len(composited_card.shape) == 3 and composited_card.shape[2] == 4)
                else composited_card
            )
            apply_post_scan_adjustments_and_save(
                source_bgr_image=bgr_only,
                output_file_path=destination_path,
                resolution_dpi=int(arguments.resolution_dpi),
                output_format=output_extension,
                jpeg_quality=int(arguments.jpeg_quality),
            )
        print(f"  -> Extracted ID-1 card: {destination_path.name}")


def handle_booklets_command(arguments: argparse.Namespace) -> None:
    """
    Execute batch booklet spread splitting, OCR orientation, and optional PDF export.

    Parameters
    ----------
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    input_directory: Path = Path(str(arguments.input_directory))
    output_directory: Path = Path(str(arguments.output_directory))
    output_directory.mkdir(parents=True, exist_ok=True)

    output_extension: str = (
        "jpg"
        if str(arguments.output_format).lower() == "jpeg"
        else str(arguments.output_format).lower()
    )
    pdf_target: Optional[Path] = (
        Path(str(arguments.compile_pdf_path)) if arguments.compile_pdf_path else None
    )

    booklet_config: BookletProcessConfiguration = BookletProcessConfiguration(
        input_directory=input_directory,
        output_directory=output_directory,
        split_dual_pages=not bool(arguments.single_page),
        enable_ocr_orientation=not bool(arguments.skip_ocr),
        spread_orientation=str(arguments.spread_orientation),
        reading_direction=str(arguments.reading_direction),
        spread_aspect_ratio_threshold=float(arguments.spread_threshold),
        rotate_even_spreads_180=bool(arguments.rotate_even_180),
        margin_padding_pixels=int(arguments.margin_padding_px),
        output_format=output_extension,
        jpeg_quality=int(arguments.jpeg_quality),
        compile_pdf_path=pdf_target,
        pdf_paper_size=str(arguments.pdf_paper_size),
        pdf_margin_millimeters=float(arguments.pdf_margin_mm),
        resolution_dpi=int(arguments.resolution_dpi),
    )

    spread_paths: list[Path] = discover_image_sequence(input_directory)
    if not spread_paths:
        print(f"[Warning] No spread images found in {input_directory}.")
        return

    written_page_paths: list[Path] = []
    global_page_counter: int = 1
    total_spreads: int = len(spread_paths)

    spread_index: int
    for spread_index in range(total_spreads):
        spread_path: Path = spread_paths[spread_index]
        spread_number: int = spread_index + 1
        print(f"[{spread_number}/{total_spreads}] Segmenting spread {spread_path.name}...")
        spread_image: Optional[np.ndarray] = cv2.imread(str(spread_path), cv2.IMREAD_COLOR)
        if spread_image is None:
            print(f"  [Warning] Could not decode {spread_path.name}.")
            continue

        if booklet_config.rotate_even_spreads_180 and (spread_number % 2 == 0):
            spread_image = cv2.rotate(spread_image, cv2.ROTATE_180)

        page_segments: list[BookletPageSegment] = segment_booklet_with_config(
            spread_image=spread_image,
            configuration=booklet_config,
        )

        segment: BookletPageSegment
        for segment in page_segments:
            page_bgr: np.ndarray = segment.page_image
            if booklet_config.enable_ocr_orientation:
                correction_angle: int = detect_upright_orientation_angle(page_bgr)
                if correction_angle != 0:
                    page_bgr = rotate_image_to_upright(page_bgr, correction_angle)

            target_filename: str = f"{global_page_counter:02d}.{output_ext}"
            destination_path: Path = output_directory / target_filename
            apply_post_scan_adjustments_and_save(
                source_bgr_image=page_bgr,
                output_file_path=destination_path,
                resolution_dpi=booklet_config.resolution_dpi,
                output_format=output_ext,
                jpeg_quality=booklet_config.jpeg_quality,
            )
            written_page_paths.append(destination_path)
            print(f"  -> Saved page {global_page_counter}: {destination_path.name}")
            global_page_counter += 1

    if booklet_config.compile_pdf_path is not None and written_page_paths:
        pdf_config: PdfCompilationConfiguration = PdfCompilationConfiguration(
            input_image_paths=written_page_paths,
            output_pdf_path=booklet_config.compile_pdf_path,
            paper_size=booklet_config.pdf_paper_size,
            margin_millimeters=booklet_config.pdf_margin_millimeters,
            resolution_dpi=booklet_config.resolution_dpi,
        )
        compiled_booklet_pdf: Path = compile_pdf_with_config(pdf_config)
        print(f"[Success] Compiled booklet PDF: {compiled_booklet_pdf}")


def handle_compile_pdf_command(arguments: argparse.Namespace) -> None:
    """
    Execute multi-image PDF compilation with virtual paper layout and fit-mode options.

    Parameters
    ----------
    arguments : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    None
    """
    raw_input_spec: str = str(arguments.input_directory)
    output_pdf_path: Path = Path(str(arguments.output_file_path))

    explicit_files: Optional[list[Path]] = None
    source_directory: Optional[Path] = None

    if "," in raw_input_spec:
        explicit_files = [
            Path(part.strip()) for part in raw_input_spec.split(",") if part.strip()
        ]
    else:
        candidate_input: Path = Path(raw_input_spec)
        if candidate_input.is_file():
            explicit_files = [candidate_input]
        else:
            source_directory = candidate_input

    image_paths: list[Path] = (
        explicit_files
        if explicit_files is not None
        else discover_image_sequence(source_directory if source_directory is not None else Path("."))
    )
    if not image_paths:
        print(f"[Error] No images found in '{raw_input_spec}' to compile.")
        return

    pdf_configuration: PdfCompilationConfiguration = PdfCompilationConfiguration(
        input_directory=source_directory,
        input_image_paths=image_paths,
        output_pdf_path=output_pdf_path,
        paper_size=str(arguments.paper_size),
        page_orientation=str(arguments.page_orientation),
        custom_width_millimeters=arguments.custom_width_mm,
        custom_height_millimeters=arguments.custom_height_mm,
        margin_millimeters=float(arguments.margin_mm),
        fit_mode=str(arguments.fit_mode),
        resolution_dpi=(
            int(arguments.resolution_dpi) if arguments.resolution_dpi is not None else None
        ),
        jpeg_compression_quality=int(arguments.jpeg_compression),
        document_title=str(arguments.document_title),
        document_author=str(arguments.document_author),
    )

    print(
        f"Compiling {len(image_paths)} image(s) into PDF ({pdf_configuration.paper_size}, "
        f"fit={pdf_configuration.fit_mode}, margin={pdf_configuration.margin_millimeters}mm): {output_pdf_path}..."
    )
    saved_pdf_path: Path = compile_pdf_with_config(pdf_configuration)
    file_size_megabytes: float = float(saved_pdf_path.stat().st_size) / (1024.0 * 1024.0)
    print(f"[Success] Compiled PDF document: {saved_pdf_path} ({file_size_megabytes:.2f} MB)")


def handle_stitch_legal_command(arguments: argparse.Namespace) -> None:
    """Execute deterministic two-pass legal stitching from CLI arguments."""
    top_image_path: Path = Path(arguments.top_image_path).resolve()
    bottom_image_path: Path = Path(arguments.bottom_image_path).resolve()
    output_path: Path = Path(arguments.output_path).resolve()
    resolution_dpi: int = int(arguments.resolution_dpi)

    if not top_image_path.exists():
        print(f"Error: Top image not found: {top_image_path}", file=sys.stderr)
        sys.exit(1)
    if not bottom_image_path.exists():
        print(f"Error: Bottom image not found: {bottom_image_path}", file=sys.stderr)
        sys.exit(1)

    top_bgr: Optional[np.ndarray] = cv2.imread(str(top_image_path), cv2.IMREAD_COLOR)
    bottom_bgr: Optional[np.ndarray] = cv2.imread(str(bottom_image_path), cv2.IMREAD_COLOR)
    if top_bgr is None or bottom_bgr is None:
        print("Error: Failed to decode input images.", file=sys.stderr)
        sys.exit(1)

    print(
        f"Stitching Legal Document from {top_image_path.name} and {bottom_image_path.name} @ {resolution_dpi} DPI..."
    )
    result: LegalStitchResult = stitch_legal_two_pass(
        pass1_top_bgr_image=top_bgr,
        pass2_bottom_upside_down_bgr_image=bottom_bgr,
        resolution_dpi=resolution_dpi,
        enable_phase_correlation=True,
    )

    if output_path.suffix.lower() == ".pdf":
        save_legal_stitch_result_to_pdf(result, output_path)
    else:
        rgb_image: np.ndarray = cv2.cvtColor(result.stitched_bgr_image, cv2.COLOR_BGR2RGB)
        pil_image: Image.Image = Image.fromarray(rgb_image)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pil_image.save(output_path, "PNG", dpi=(float(resolution_dpi), float(resolution_dpi)))

    print(
        f"[Success] Stitched Legal saved: {output_path} (Confidence: {result.correlation_confidence * 100:.1f}%)"
    )


def main() -> None:
    """
    Main CLI entry point for ``process_cli``.

    Returns
    -------
    None
    """
    parser: argparse.ArgumentParser = build_argument_parser()
    arguments: argparse.Namespace = parser.parse_args()

    if arguments.command is None:
        parser.print_help()
        sys.exit(0)

    if str(arguments.command) in ("cards", "card"):
        if str(getattr(arguments, "paper_size", "")) == "custom":
            pass
        handle_cards_command(arguments)
    elif str(arguments.command) in ("booklets", "booklet"):
        handle_booklets_command(arguments)
    elif str(arguments.command) in ("stitch-legal", "legal-stitch"):
        handle_stitch_legal_command(arguments)
    elif str(arguments.command) == "compile-pdf":
        if str(arguments.paper_size) == "custom" and (
            arguments.custom_width_mm is None or arguments.custom_height_mm is None
        ):
            parser.error("--paper-size custom requires both --width-mm and --height-mm.")
        try:
            handle_compile_pdf_command(arguments)
        except ValueError as validation_error:
            parser.error(str(validation_error))


if __name__ == "__main__":
    main()
