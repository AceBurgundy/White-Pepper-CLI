"""
High-fidelity PDF document compiler, virtual paper layout engine, and sequence aggregator.

Supports standard ISO/ANSI virtual page formats (including US Legal ``8.5 x 14.0 in``),
custom millimeter dimensions, page margins, placement fit modes (``contain``, ``fill``,
``stretch``, ``original``), JPEG stream recompression, and PDF metadata embedding.
"""

from __future__ import annotations

# DPI = Dots Per Inch
# PDF = Portable Document Format
# RGB = Red Green Blue
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format

import io
from pathlib import Path
import re
from typing import Optional

PYMUPDF_AVAILABLE: bool = False
try:
    import pymupdf as fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz  # type: ignore

        PYMUPDF_AVAILABLE = True
    except ImportError:
        fitz: Optional[object] = None  # type: ignore
        PYMUPDF_AVAILABLE = False

from PIL import Image

from white_pepper.algorithms.geometry import (
    PAPER_SIZE_REGISTRY,
    POINTS_PER_INCH,
    PaperSizeSpec,
    millimeters_to_points,
)
from white_pepper.config import SUPPORTED_PDF_FIT_MODES, PdfCompilationConfiguration


def natural_sort_key(file_path: Path) -> list[int | str]:
    """
    Generate a human/natural alphanumeric sort key for a filesystem path.

    Parameters
    ----------
    file_path : Path
        Filesystem path whose stem will be tokenized into numeric and text segments.

    Returns
    -------
    list[int | str]
        Ordered list of integer and lowercase string tokens for natural sorting.
    """
    file_stem: str = file_path.stem
    tokens: list[str] = re.split(r"(\d+)", file_stem)
    sorting_key: list[int | str] = [
        int(token) if token.isdigit() else token.lower() for token in tokens if token
    ]
    return sorting_key


def discover_image_sequence(
    input_directory: Path,
    supported_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"),
) -> list[Path]:
    """
    Discover and naturally sort all supported raster image files inside a directory.

    Parameters
    ----------
    input_directory : Path
        Directory scanned for image files.
    supported_extensions : tuple[str, ...], optional
        Tuple of accepted lowercase file extensions, by default
        ``(".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")``.

    Returns
    -------
    list[Path]
        Naturally sorted list of image file paths.
    """
    if not input_directory.exists() or not input_directory.is_dir():
        return []

    image_paths: list[Path] = [
        file_path
        for file_path in input_directory.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions
    ]
    image_paths.sort(key=natural_sort_key)
    return image_paths


def _resolve_virtual_page_points(
    native_width_points: float,
    native_height_points: float,
    paper_size: str,
    page_orientation: str,
    custom_width_millimeters: Optional[float],
    custom_height_millimeters: Optional[float],
    margin_points: float,
) -> tuple[float, float]:
    """
    Determine the target virtual PDF page width and height in typographic points.

    Parameters
    ----------
    native_width_points : float
        Source image width in PDF points at ``resolution_dpi``.
    native_height_points : float
        Source image height in PDF points at ``resolution_dpi``.
    paper_size : str
        Paper size key (``"auto"``, ``"custom"``, or a ``PAPER_SIZE_REGISTRY`` key).
    page_orientation : str
        Orientation mode (``"auto"``, ``"portrait"``, or ``"landscape"``).
    custom_width_millimeters : Optional[float]
        Custom page width in millimeters when ``paper_size == "custom"``.
    custom_height_millimeters : Optional[float]
        Custom page height in millimeters when ``paper_size == "custom"``.
    margin_points : float
        Uniform page margin in PDF points.

    Returns
    -------
    tuple[float, float]
        Two-element tuple ``(page_width_points, page_height_points)``.

    Raises
    ------
    ValueError
        If an unknown paper size, invalid orientation, or missing custom dimension is supplied.
    """
    normalized_size: str = paper_size.strip().lower()
    normalized_orientation: str = page_orientation.strip().lower()
    if normalized_orientation not in ("auto", "portrait", "landscape"):
        raise ValueError(
            f"Unsupported PDF page orientation '{page_orientation}'. Expected 'auto', 'portrait', or 'landscape'."
        )

    page_width_points: float
    page_height_points: float

    if normalized_size == "auto":
        page_width_points = native_width_points + (2.0 * margin_points)
        page_height_points = native_height_points + (2.0 * margin_points)
        if normalized_orientation == "portrait" and page_width_points > page_height_points:
            swapped_auto_width: float = page_height_points
            swapped_auto_height: float = page_width_points
            page_width_points = swapped_auto_width
            page_height_points = swapped_auto_height
        elif normalized_orientation == "landscape" and page_width_points < page_height_points:
            swapped_landscape_width: float = page_height_points
            swapped_landscape_height: float = page_width_points
            page_width_points = swapped_landscape_width
            page_height_points = swapped_landscape_height
        return (page_width_points, page_height_points)

    if normalized_size == "custom":
        if (
            custom_width_millimeters is None
            or custom_height_millimeters is None
            or custom_width_millimeters <= 0.0
            or custom_height_millimeters <= 0.0
        ):
            raise ValueError(
                "Positive custom_width_millimeters and custom_height_millimeters are required when paper_size='custom'."
            )
        page_width_points = millimeters_to_points(custom_width_millimeters)
        page_height_points = millimeters_to_points(custom_height_millimeters)
    else:
        if normalized_size not in PAPER_SIZE_REGISTRY:
            supported_keys: str = ", ".join(("auto",) + tuple(PAPER_SIZE_REGISTRY.keys()) + ("custom",))
            raise ValueError(
                f"Unknown PDF paper size '{paper_size}'. Supported choices: {supported_keys}."
            )
        paper_spec: PaperSizeSpec = PAPER_SIZE_REGISTRY[normalized_size]
        page_width_points = paper_spec.width_points
        page_height_points = paper_spec.height_points

    smaller_side: float = min(page_width_points, page_height_points)
    larger_side: float = max(page_width_points, page_height_points)

    if normalized_orientation == "portrait":
        page_width_points = smaller_side
        page_height_points = larger_side
    elif normalized_orientation == "landscape":
        page_width_points = larger_side
        page_height_points = smaller_side
    else:
        if native_width_points > native_height_points:
            page_width_points = larger_side
            page_height_points = smaller_side
        else:
            page_width_points = smaller_side
            page_height_points = larger_side

    return (page_width_points, page_height_points)


def _prepare_image_and_placement(
    source_image: Image.Image,
    native_width_points: float,
    native_height_points: float,
    inner_x0: float,
    inner_y0: float,
    inner_width: float,
    inner_height: float,
    fit_mode: str,
) -> tuple[Image.Image, tuple[float, float, float, float]]:
    """
    Compute the cropped/fitted Pillow image and its exact placement rectangle in points.

    Parameters
    ----------
    source_image : Image.Image
        RGB Pillow image for the current page.
    native_width_points : float
        Native image width in PDF points.
    native_height_points : float
        Native image height in PDF points.
    inner_x0 : float
        Left coordinate of the inner content box in points.
    inner_y0 : float
        Top coordinate of the inner content box in points.
    inner_width : float
        Available width inside page margins in points.
    inner_height : float
        Available height inside page margins in points.
    fit_mode : str
        Placement mode (``"contain"``, ``"fill"``, ``"stretch"``, or ``"original"``).

    Returns
    -------
    tuple[Image.Image, tuple[float, float, float, float]]
        Prepared Pillow image and target ``(x0, y0, x1, y1)`` rectangle in PDF points.
    """
    normalized_fit: str = fit_mode.strip().lower()

    if normalized_fit == "stretch":
        stretch_box: tuple[float, float, float, float] = (
            inner_x0,
            inner_y0,
            inner_x0 + inner_width,
            inner_y0 + inner_height,
        )
        return (source_image, stretch_box)

    if normalized_fit == "fill":
        target_aspect: float = inner_width / max(0.01, inner_height)
        image_width_px: int = int(source_image.width)
        image_height_px: int = int(source_image.height)
        source_aspect: float = float(image_width_px) / float(max(1, image_height_px))

        cropped_image: Image.Image = source_image
        if abs(source_aspect - target_aspect) > 0.005:
            if source_aspect > target_aspect:
                desired_width_px: int = max(1, int(round(float(image_height_px) * target_aspect)))
                crop_left: int = max(0, (image_width_px - desired_width_px) // 2)
                cropped_image = source_image.crop(
                    (crop_left, 0, crop_left + desired_width_px, image_height_px)
                )
            else:
                desired_height_px: int = max(1, int(round(float(image_width_px) / target_aspect)))
                crop_top: int = max(0, (image_height_px - desired_height_px) // 2)
                cropped_image = source_image.crop(
                    (0, crop_top, image_width_px, crop_top + desired_height_px)
                )

        fill_box: tuple[float, float, float, float] = (
            inner_x0,
            inner_y0,
            inner_x0 + inner_width,
            inner_y0 + inner_height,
        )
        return (cropped_image, fill_box)

    if normalized_fit == "original":
        placed_width: float = min(inner_width, native_width_points)
        placed_height: float = min(inner_height, native_height_points)
        if native_width_points > inner_width or native_height_points > inner_height:
            clamp_scale: float = min(
                inner_width / max(0.01, native_width_points),
                inner_height / max(0.01, native_height_points),
            )
            placed_width = native_width_points * clamp_scale
            placed_height = native_height_points * clamp_scale

        orig_x0: float = inner_x0 + ((inner_width - placed_width) / 2.0)
        orig_y0: float = inner_y0 + ((inner_height - placed_height) / 2.0)
        original_box: tuple[float, float, float, float] = (
            orig_x0,
            orig_y0,
            orig_x0 + placed_width,
            orig_y0 + placed_height,
        )
        return (source_image, original_box)

    contain_scale: float = min(
        inner_width / max(0.01, native_width_points),
        inner_height / max(0.01, native_height_points),
    )
    scaled_width: float = native_width_points * contain_scale
    scaled_height: float = native_height_points * contain_scale
    contain_x0: float = inner_x0 + ((inner_width - scaled_width) / 2.0)
    contain_y0: float = inner_y0 + ((inner_height - scaled_height) / 2.0)
    contain_box: tuple[float, float, float, float] = (
        contain_x0,
        contain_y0,
        contain_x0 + scaled_width,
        contain_y0 + scaled_height,
    )
    return (source_image, contain_box)


def compile_images_to_pdf(
    image_paths: list[Path],
    output_pdf_path: Path,
    resolution_dpi: int = 300,
    paper_size: str = "auto",
    page_orientation: str = "auto",
    custom_width_millimeters: Optional[float] = None,
    custom_height_millimeters: Optional[float] = None,
    margin_millimeters: float = 0.0,
    fit_mode: str = "contain",
    jpeg_compression_quality: int = 0,
    document_title: str = "",
    document_author: str = "",
) -> Path:
    """
    Compile an ordered sequence of raster images into a multi-page PDF document.

    Parameters
    ----------
    image_paths : list[Path]
        Ordered list of source image files to place into the PDF.
    output_pdf_path : Path
        Target filesystem path for the compiled PDF.
    resolution_dpi : int, optional
        Reference DPI used to translate pixel dimensions into physical points, by default ``300``.
    paper_size : str, optional
        Target page size (``"auto"``, ``"custom"``, or a ``PAPER_SIZE_REGISTRY`` key such as
        ``"a4"``, ``"letter"``, or ``"legal"``), by default ``"auto"``.
    page_orientation : str, optional
        Virtual page orientation (``"auto"``, ``"portrait"``, or ``"landscape"``),
        by default ``"auto"``.
    custom_width_millimeters : Optional[float], optional
        Custom page width in millimeters when ``paper_size == "custom"``, by default ``None``.
    custom_height_millimeters : Optional[float], optional
        Custom page height in millimeters when ``paper_size == "custom"``, by default ``None``.
    margin_millimeters : float, optional
        Uniform page margin inset in millimeters on all four sides, by default ``0.0``.
    fit_mode : str, optional
        Image placement strategy (``"contain"``, ``"fill"``, ``"stretch"``, or ``"original"``),
        by default ``"contain"``.
    jpeg_compression_quality : int, optional
        JPEG stream compression quality ``[1, 100]``, or ``0`` to retain lossless PNG streams,
        by default ``0``.
    document_title : str, optional
        PDF ``Title`` metadata string, by default ``""``.
    document_author : str, optional
        PDF ``Author`` metadata string, by default ``""``.

    Returns
    -------
    Path
        Path to the saved PDF document.

    Raises
    ------
    ValueError
        If ``image_paths`` is empty, ``fit_mode`` is invalid, or ``margin_millimeters``
        leaves no positive inner content area.
    RuntimeError
        If none of the supplied image paths can be decoded.
    """
    if not image_paths:
        raise ValueError("Cannot compile PDF: No input image paths provided.")

    if margin_millimeters < 0.0:
        raise ValueError(f"PDF margin_millimeters must be non-negative (received {margin_millimeters}).")

    normalized_fit: str = fit_mode.strip().lower()
    if normalized_fit not in SUPPORTED_PDF_FIT_MODES:
        supported_fits: str = ", ".join(SUPPORTED_PDF_FIT_MODES)
        raise ValueError(f"Unsupported PDF fit_mode '{fit_mode}'. Expected one of: {supported_fits}.")

    effective_dpi: int = max(1, resolution_dpi)
    margin_points: float = millimeters_to_points(margin_millimeters)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if PYMUPDF_AVAILABLE and fitz is not None:
        document: object = fitz.open()  # type: ignore[attr-defined]
        inserted_page_count: int = 0

        image_path: Path
        for image_path in image_paths:
            try:
                loaded_pil: Image.Image = Image.open(image_path)
                rgb_pil: Image.Image = loaded_pil.convert("RGB")
            except Exception as open_error:
                print(f"  [Warning] Skipping unreadable image {image_path}: {open_error}")
                continue

            native_width_points: float = (float(rgb_pil.width) / float(effective_dpi)) * POINTS_PER_INCH
            native_height_points: float = (float(rgb_pil.height) / float(effective_dpi)) * POINTS_PER_INCH

            page_dims: tuple[float, float] = _resolve_virtual_page_points(
                native_width_points=native_width_points,
                native_height_points=native_height_points,
                paper_size=paper_size,
                page_orientation=page_orientation,
                custom_width_millimeters=custom_width_millimeters,
                custom_height_millimeters=custom_height_millimeters,
                margin_points=margin_points,
            )
            page_width_pt: float = page_dims[0]
            page_height_pt: float = page_dims[1]

            inner_width_pt: float = page_width_pt - (2.0 * margin_points)
            inner_height_pt: float = page_height_pt - (2.0 * margin_points)
            if inner_width_pt <= 1.0 or inner_height_pt <= 1.0:
                document.close()
                raise ValueError(
                    f"Margin {margin_millimeters} mm exceeds half of target '{paper_size}' page dimensions."
                )

            placement_pair: tuple[Image.Image, tuple[float, float, float, float]] = (
                _prepare_image_and_placement(
                    source_image=rgb_pil,
                    native_width_points=native_width_points,
                    native_height_points=native_height_points,
                    inner_x0=margin_points,
                    inner_y0=margin_points,
                    inner_width=inner_width_pt,
                    inner_height=inner_height_pt,
                    fit_mode=normalized_fit,
                )
            )
            prepared_pil: Image.Image = placement_pair[0]
            placement_coords: tuple[float, float, float, float] = placement_pair[1]

            encoded_buffer: io.BytesIO = io.BytesIO()
            if 0 < jpeg_compression_quality < 100:
                clamped_jpeg: int = max(1, min(99, jpeg_compression_quality))
                prepared_pil.save(encoded_buffer, format="JPEG", quality=clamped_jpeg)
            else:
                prepared_pil.save(encoded_buffer, format="PNG")
            stream_bytes: bytes = encoded_buffer.getvalue()

            pdf_page: object = document.new_page(  # type: ignore[attr-defined]
                width=page_width_pt,
                height=page_height_pt,
            )
            target_rectangle: object = fitz.Rect(  # type: ignore[attr-defined]
                placement_coords[0],
                placement_coords[1],
                placement_coords[2],
                placement_coords[3],
            )
            pdf_page.insert_image(  # type: ignore[attr-defined]
                target_rectangle,
                stream=stream_bytes,
                keep_proportion=False,
            )
            inserted_page_count += 1

        if inserted_page_count == 0:
            document.close()  # type: ignore[attr-defined]
            raise RuntimeError("No valid images could be loaded for PDF compilation.")

        if document_title or document_author:
            metadata_dict: dict[str, str] = {
                "title": document_title,
                "author": document_author,
                "creator": "white-pepper",
                "producer": "white-pepper PDF Builder",
            }
            document.set_metadata(metadata_dict)  # type: ignore[attr-defined]

        document.save(str(output_pdf_path), garbage=4, deflate=True)  # type: ignore[attr-defined]
        document.close()  # type: ignore[attr-defined]
        return output_pdf_path

    pillow_images: list[Image.Image] = []
    first_image: Optional[Image.Image] = None

    fallback_path: Path
    for fallback_path in image_paths:
        try:
            loaded_image: Image.Image = Image.open(fallback_path)
            rgb_image: Image.Image = loaded_image.convert("RGB")
            if first_image is None:
                first_image = rgb_image
            else:
                pillow_images.append(rgb_image)
        except Exception as pillow_error:
            print(f"  [Warning] Pillow could not open {fallback_path}: {pillow_error}")

    if first_image is None:
        raise RuntimeError("No valid images could be loaded for PDF compilation.")

    first_image.save(
        str(output_pdf_path),
        save_all=True,
        append_images=pillow_images,
        resolution=float(effective_dpi),
        title=document_title or None,
        author=document_author or None,
    )
    return output_pdf_path


def compile_pdf_with_config(configuration: PdfCompilationConfiguration) -> Path:
    """
    Compile images into a PDF document using a ``PdfCompilationConfiguration`` contract.

    Parameters
    ----------
    configuration : PdfCompilationConfiguration
        Typed PDF layout, paper size, margin, fit-mode, and metadata configuration.

    Returns
    -------
    Path
        Path to the compiled PDF document.

    Raises
    ------
    ValueError
        If neither ``input_image_paths`` nor a non-empty ``input_directory`` is provided.
    """
    resolved_paths: list[Path]
    if configuration.input_image_paths is not None and len(configuration.input_image_paths) > 0:
        resolved_paths = list(configuration.input_image_paths)
    elif configuration.input_directory is not None:
        resolved_paths = discover_image_sequence(configuration.input_directory)
    else:
        raise ValueError(
            "PdfCompilationConfiguration requires either input_image_paths or input_directory."
        )

    if not resolved_paths:
        raise ValueError("No valid input images discovered for PDF compilation.")

    saved_pdf: Path = compile_images_to_pdf(
        image_paths=resolved_paths,
        output_pdf_path=configuration.output_pdf_path,
        resolution_dpi=configuration.resolution_dpi,
        paper_size=configuration.paper_size,
        page_orientation=configuration.page_orientation,
        custom_width_millimeters=configuration.custom_width_millimeters,
        custom_height_millimeters=configuration.custom_height_millimeters,
        margin_millimeters=configuration.margin_millimeters,
        fit_mode=configuration.fit_mode,
        jpeg_compression_quality=configuration.jpeg_compression_quality,
        document_title=configuration.document_title,
        document_author=configuration.document_author,
    )
    return saved_pdf
