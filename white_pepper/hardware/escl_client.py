"""
Wireless eSCL (Apple AirScan / Mopria) REST API client and post-scan raster pipeline.

Provides network discovery, capability inspection, XML scan job submission,
deterministic software bounding-box clipping for firmware that ignores
``<pwg:ScanRegion>``, post-scan tone/rotation/crop processing, and multi-format export.
"""

from __future__ import annotations

# eSCL = Enhanced Scanner Client Language
# COM = Component Object Model
# DPI = Dots Per Inch
# PDF = Portable Document Format
# RGB = Red Green Blue
# BGR = Blue Green Red
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format
# HTTP = Hypertext Transfer Protocol
# TCP = Transmission Control Protocol
# URL = Uniform Resource Locator
# XML = Extensible Markup Language
# ARP = Address Resolution Protocol
# IPv4 = Internet Protocol Version 4
# UUID = Universally Unique Identifier

import io
from pathlib import Path
import re
import socket
import subprocess
import time
from typing import Optional
import urllib.error
import urllib.request

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

import cv2
import numpy as np
from PIL import Image

from white_pepper.algorithms.geometry import (
    PLATEN_MAX_HEIGHT_INCHES,
    PLATEN_MAX_WIDTH_INCHES,
    ResolvedScanRegion,
    resolve_scan_region,
)
from white_pepper.config import ESCL_COLOR_MODE_MAPPING, ESCL_INTENT_MAPPING
from white_pepper.utils.audio import play_completion_beep

DEFAULT_ESCL_IP: str = "192.168.1.150"
DEFAULT_ESCL_PORT: int = 8080


def crop_whitespace_borders(
    source_bgr_image: np.ndarray,
    resolution_dpi: int = 300,
    white_threshold: int = 245,
) -> np.ndarray:
    """
    Automatically trim uniform light/white borders around foreground content.

    Parameters
    ----------
    source_bgr_image : np.ndarray
        Input 3-channel BGR or 2-channel grayscale image array.
    resolution_dpi : int, optional
        Optical resolution used to compute a proportional safety margin, by default ``300``.
    white_threshold : int, optional
        Grayscale intensity threshold ``[0, 255]`` above which pixels are treated as background,
        by default ``245``.

    Returns
    -------
    np.ndarray
        Cropped image array, or the original array if no foreground contour is detected.
    """
    if source_bgr_image.size == 0:
        return source_bgr_image

    grayscale_layer: np.ndarray
    if len(source_bgr_image.shape) == 3 and source_bgr_image.shape[2] >= 3:
        grayscale_layer = cv2.cvtColor(source_bgr_image, cv2.COLOR_BGR2GRAY)
    else:
        grayscale_layer = source_bgr_image

    threshold_result: tuple[float, np.ndarray] = cv2.threshold(
        grayscale_layer,
        float(white_threshold),
        255.0,
        cv2.THRESH_BINARY_INV,
    )
    foreground_mask: np.ndarray = threshold_result[1]

    morphology_kernel: np.ndarray = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    cleaned_mask: np.ndarray = cv2.morphologyEx(
        foreground_mask,
        cv2.MORPH_OPEN,
        morphology_kernel,
    )

    foreground_points: Optional[np.ndarray] = cv2.findNonZero(cleaned_mask)
    if foreground_points is None:
        return source_bgr_image

    bounding_box: tuple[int, int, int, int] = cv2.boundingRect(foreground_points)
    box_horizontal_start: int = bounding_box[0]
    box_vertical_start: int = bounding_box[1]
    box_width: int = bounding_box[2]
    box_height: int = bounding_box[3]

    image_height: int = int(source_bgr_image.shape[0])
    image_width: int = int(source_bgr_image.shape[1])
    safety_margin_pixels: int = max(4, int(round(float(resolution_dpi) * 0.04)))

    crop_horizontal_start: int = max(0, box_horizontal_start - safety_margin_pixels)
    crop_vertical_start: int = max(0, box_vertical_start - safety_margin_pixels)
    crop_horizontal_end: int = min(image_width, box_horizontal_start + box_width + safety_margin_pixels)
    crop_vertical_end: int = min(image_height, box_vertical_start + box_height + safety_margin_pixels)

    if crop_horizontal_end <= crop_horizontal_start or crop_vertical_end <= crop_vertical_start:
        return source_bgr_image

    cropped_result: np.ndarray = source_bgr_image[
        crop_vertical_start:crop_vertical_end, crop_horizontal_start:crop_horizontal_end
    ]
    return cropped_result


def apply_post_scan_adjustments_and_save(
    source_bgr_image: np.ndarray,
    output_file_path: Path,
    resolution_dpi: int = 300,
    color_mode: str = "color",
    brightness: int = 0,
    contrast: int = 0,
    rotation_degrees: int = 0,
    auto_crop_whitespace: bool = False,
    output_format: str = "png",
    jpeg_quality: int = 95,
    apply_software_tone: bool = False,
) -> Path:
    """
    Apply optional tone, rotation, auto-crop, and channel conversions and save to disk.

    Parameters
    ----------
    source_bgr_image : np.ndarray
        Decoded scan image in BGR or grayscale format.
    output_file_path : Path
        Target file path where the encoded output will be written.
    resolution_dpi : int, optional
        Physical DPI metadata embedded into the output file, by default ``300``.
    color_mode : str, optional
        Target channel representation (``"color"``, ``"grayscale"``, or ``"bw"``),
        by default ``"color"``.
    brightness : int, optional
        Brightness offset in ``[-100, 100]``, by default ``0``.
    contrast : int, optional
        Contrast offset in ``[-100, 100]``, by default ``0``.
    rotation_degrees : int, optional
        Clockwise cardinal rotation in ``{0, 90, 180, 270}``, by default ``0``.
    auto_crop_whitespace : bool, optional
        Trim surrounding white borders when ``True``, by default ``False``.
    output_format : str, optional
        Output format (``"png"``, ``"jpg"``, ``"jpeg"``, ``"tiff"``, ``"bmp"``, ``"pdf"``),
        by default ``"png"``.
    jpeg_quality : int, optional
        JPEG quality factor ``[1, 100]``, by default ``95``.
    apply_software_tone : bool, optional
        Apply software brightness/contrast scaling when hardware did not apply it,
        by default ``False``.

    Returns
    -------
    Path
        Saved file path on disk.

    Raises
    ------
    ValueError
        If ``source_bgr_image`` is empty or ``rotation_degrees`` is invalid.
    """
    if source_bgr_image is None or source_bgr_image.size == 0:
        raise ValueError("Cannot save scan: source image array is empty.")

    if rotation_degrees not in (0, 90, 180, 270):
        raise ValueError(
            f"Unsupported rotation angle {rotation_degrees}. Expected 0, 90, 180, or 270."
        )

    working_image: np.ndarray = source_bgr_image.copy()
    if len(working_image.shape) == 2:
        working_image = cv2.cvtColor(working_image, cv2.COLOR_GRAY2BGR)

    if apply_software_tone and (brightness != 0 or contrast != 0):
        clamped_brightness: int = max(-100, min(100, brightness))
        clamped_contrast: int = max(-100, min(100, contrast))
        contrast_gain: float = max(0.1, 1.0 + (float(clamped_contrast) / 100.0))
        brightness_bias: float = float(clamped_brightness) * 1.275
        working_image = cv2.convertScaleAbs(
            working_image,
            alpha=contrast_gain,
            beta=brightness_bias,
        )

    if rotation_degrees == 90:
        working_image = cv2.rotate(working_image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_degrees == 180:
        working_image = cv2.rotate(working_image, cv2.ROTATE_180)
    elif rotation_degrees == 270:
        working_image = cv2.rotate(working_image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    if auto_crop_whitespace:
        working_image = crop_whitespace_borders(
            working_image,
            resolution_dpi=resolution_dpi,
        )

    normalized_color: str = color_mode.strip().lower()
    pillow_image: Image.Image

    if normalized_color == "grayscale":
        grayscale_output: np.ndarray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
        pillow_image = Image.fromarray(grayscale_output, mode="L")
    elif normalized_color == "bw":
        grayscale_source: np.ndarray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
        otsu_result: tuple[float, np.ndarray] = cv2.threshold(
            grayscale_source,
            0.0,
            255.0,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        binary_output: np.ndarray = otsu_result[1]
        pillow_image = Image.fromarray(binary_output, mode="L")
    else:
        rgb_output: np.ndarray = cv2.cvtColor(working_image, cv2.COLOR_BGR2RGB)
        pillow_image = Image.fromarray(rgb_output, mode="RGB")

    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    effective_format: str = output_format.strip().lower().lstrip(".")
    suffix_extension: str = output_file_path.suffix.strip().lower().lstrip(".")
    if effective_format == "png" and suffix_extension in ("jpg", "jpeg", "tiff", "tif", "bmp", "pdf"):
        effective_format = "tiff" if suffix_extension == "tif" else suffix_extension
    if effective_format == "jpeg":
        effective_format = "jpg"

    clamped_quality: int = max(1, min(100, jpeg_quality))
    dpi_tuple: tuple[float, float] = (float(resolution_dpi), float(resolution_dpi))

    if effective_format == "pdf":
        if PYMUPDF_AVAILABLE and fitz is not None:
            image_buffer: io.BytesIO = io.BytesIO()
            if clamped_quality < 100:
                rgb_for_jpeg: Image.Image = (
                    pillow_image if pillow_image.mode in ("RGB", "L") else pillow_image.convert("RGB")
                )
                rgb_for_jpeg.save(image_buffer, format="JPEG", quality=clamped_quality)
            else:
                pillow_image.save(image_buffer, format="PNG")
            encoded_stream: bytes = image_buffer.getvalue()

            page_width_points: float = (float(pillow_image.width) / float(resolution_dpi)) * 72.0
            page_height_points: float = (float(pillow_image.height) / float(resolution_dpi)) * 72.0

            pdf_document: object = fitz.open()  # type: ignore[attr-defined]
            pdf_page: object = pdf_document.new_page(  # type: ignore[attr-defined]
                width=page_width_points,
                height=page_height_points,
            )
            pdf_page.insert_image(  # type: ignore[attr-defined]
                pdf_page.rect,  # type: ignore[attr-defined]
                stream=encoded_stream,
            )
            pdf_document.save(str(output_file_path), garbage=4, deflate=True)  # type: ignore[attr-defined]
            pdf_document.close()  # type: ignore[attr-defined]
        else:
            rgb_for_pdf: Image.Image = (
                pillow_image.convert("RGB") if pillow_image.mode != "RGB" else pillow_image
            )
            rgb_for_pdf.save(str(output_file_path), format="PDF", resolution=float(resolution_dpi))
    elif effective_format == "jpg":
        pillow_image.save(
            str(output_file_path),
            format="JPEG",
            quality=clamped_quality,
            dpi=dpi_tuple,
        )
    elif effective_format == "tiff":
        pillow_image.save(
            str(output_file_path),
            format="TIFF",
            compression="tiff_deflate",
            dpi=dpi_tuple,
        )
    elif effective_format == "bmp":
        pillow_image.save(
            str(output_file_path),
            format="BMP",
            dpi=dpi_tuple,
        )
    else:
        pillow_image.save(
            str(output_file_path),
            format="PNG",
            dpi=dpi_tuple,
        )

    return output_file_path


def decode_and_clip_escl_payload(
    document_data: bytes,
    content_type: str,
    resolution_dpi: int,
    resolved_region: ResolvedScanRegion,
) -> np.ndarray:
    """
    Decode raw eSCL PDF or raster bytes and enforce software platen clipping.

    Because certain HP eSCL scanner firmwares ignore ``<pwg:ScanRegion>`` and return
    a full-platen canvas, this function deterministically clips the decoded page or
    raster matrix to ``resolved_region`` whenever ``not resolved_region.is_full_platen``.

    Parameters
    ----------
    document_data : bytes
        Raw HTTP response payload returned by ``/NextDocument``.
    content_type : str
        HTTP ``Content-Type`` header accompanying the payload.
    resolution_dpi : int
        Target rasterization resolution in dots per inch.
    resolved_region : ResolvedScanRegion
        Validated physical scan bounding box.

    Returns
    -------
    np.ndarray
        Decoded and region-clipped 3-channel BGR image array.

    Raises
    ------
    RuntimeError
        If the payload cannot be decoded as either PDF or raster image data.
    """
    is_pdf_payload: bool = ("pdf" in content_type.lower()) or document_data.startswith(b"%PDF")

    if PYMUPDF_AVAILABLE and fitz is not None and is_pdf_payload:
        pdf_document: object = fitz.open(stream=document_data, filetype="pdf")  # type: ignore[attr-defined]
        try:
            first_page: object = pdf_document[0]  # type: ignore[index]
            page_width_points: float = float(first_page.rect.width)  # type: ignore[attr-defined]
            page_height_points: float = float(first_page.rect.height)  # type: ignore[attr-defined]

            clip_rectangle: Optional[object] = None
            exceeds_requested_box: bool = False
            if not resolved_region.is_full_platen:
                # Only clip if the returned PDF page is larger than the requested region
                exceeds_requested_box = (
                    (page_width_points - resolved_region.width_points > 2.0)
                    or (page_height_points - resolved_region.height_points > 2.0)
                    or (resolved_region.offset_x_points > 0.5)
                    or (resolved_region.offset_y_points > 0.5)
                )
                if exceeds_requested_box:
                    clip_x0: float = max(
                        0.0,
                        min(page_width_points - 1.0, resolved_region.offset_x_points),
                    )
                    clip_y0: float = max(
                        0.0,
                        min(page_height_points - 1.0, resolved_region.offset_y_points),
                    )
                    clip_x1: float = max(
                        clip_x0 + 1.0,
                        min(
                            page_width_points,
                            resolved_region.offset_x_points + resolved_region.width_points,
                        ),
                    )
                    clip_y1: float = max(
                        clip_y0 + 1.0,
                        min(
                            page_height_points,
                            resolved_region.offset_y_points + resolved_region.height_points,
                        ),
                    )
                    clip_rectangle = fitz.Rect(clip_x0, clip_y0, clip_x1, clip_y1)  # type: ignore[attr-defined]

            if not exceeds_requested_box:
                embedded_image_list: list[tuple[object, ...]] = list(
                    first_page.get_images(full=True)  # type: ignore[attr-defined]
                )
                if len(embedded_image_list) == 1:
                    image_cross_reference: int = int(embedded_image_list[0][0])  # type: ignore[arg-type]
                    extracted_image_dictionary: dict[str, object] = (
                        pdf_document.extract_image(image_cross_reference)  # type: ignore[attr-defined]
                    )
                    raw_image_bytes: Optional[bytes] = extracted_image_dictionary.get("image")  # type: ignore[assignment]
                    if isinstance(raw_image_bytes, bytes) and len(raw_image_bytes) > 0:
                        pdf_image_buffer: np.ndarray = np.frombuffer(raw_image_bytes, dtype=np.uint8)
                        native_pdf_bgr: Optional[np.ndarray] = cv2.imdecode(
                            pdf_image_buffer, cv2.IMREAD_COLOR
                        )
                        if native_pdf_bgr is not None:
                            return native_pdf_bgr

            rendered_pixmap: object = first_page.get_pixmap(  # type: ignore[attr-defined]
                dpi=resolution_dpi,
                clip=clip_rectangle,
                alpha=False,
            )
            pixmap_height: int = int(rendered_pixmap.height)  # type: ignore[attr-defined]
            pixmap_width: int = int(rendered_pixmap.width)  # type: ignore[attr-defined]
            pixmap_channels: int = int(rendered_pixmap.n)  # type: ignore[attr-defined]

            raw_samples: np.ndarray = np.frombuffer(
                rendered_pixmap.samples,  # type: ignore[attr-defined]
                dtype=np.uint8,
            )
            reshaped_samples: np.ndarray = raw_samples.reshape(
                (pixmap_height, pixmap_width, pixmap_channels)
            )
            bgr_from_pdf: np.ndarray
            if pixmap_channels == 1:
                bgr_from_pdf = cv2.cvtColor(reshaped_samples, cv2.COLOR_GRAY2BGR)
            else:
                bgr_from_pdf = cv2.cvtColor(reshaped_samples, cv2.COLOR_RGB2BGR)
            return bgr_from_pdf
        finally:
            pdf_document.close()  # type: ignore[attr-defined]

    encoded_buffer: np.ndarray = np.frombuffer(document_data, dtype=np.uint8)
    decoded_bgr: Optional[np.ndarray] = cv2.imdecode(encoded_buffer, cv2.IMREAD_COLOR)
    if decoded_bgr is None:
        raise RuntimeError("Failed to decode image data received from eSCL scanner.")

    if not resolved_region.is_full_platen:
        pixel_bounds: tuple[int, int, int, int] = resolved_region.pixel_bounds(resolution_dpi)
        horizontal_start_pixels: int = pixel_bounds[0]
        vertical_start_pixels: int = pixel_bounds[1]
        target_width_pixels: int = pixel_bounds[2]
        target_height_pixels: int = pixel_bounds[3]

        raster_height: int = int(decoded_bgr.shape[0])
        raster_width: int = int(decoded_bgr.shape[1])

        exceeds_raster_box: bool = (
            (raster_width - target_width_pixels > 4)
            or (raster_height - target_height_pixels > 4)
            or (horizontal_start_pixels > 0)
            or (vertical_start_pixels > 0)
        )
        if exceeds_raster_box:
            clamped_horizontal_start: int = max(0, min(raster_width - 1, horizontal_start_pixels))
            clamped_vertical_start: int = max(0, min(raster_height - 1, vertical_start_pixels))
            clamped_horizontal_end: int = max(
                clamped_horizontal_start + 1, min(raster_width, clamped_horizontal_start + target_width_pixels)
            )
            clamped_vertical_end: int = max(
                clamped_vertical_start + 1, min(raster_height, clamped_vertical_start + target_height_pixels)
            )
            decoded_bgr = decoded_bgr[clamped_vertical_start:clamped_vertical_end, clamped_horizontal_start:clamped_horizontal_end]

    return decoded_bgr


class EsclClient:
    """
    HTTP client for Apple AirScan / Mopria eSCL network flatbed scanners.

    Attributes
    ----------
    host_address : str
        IPv4 address or hostname of the target eSCL scanner.
    port_number : int
        TCP port serving the ``/eSCL`` endpoint.
    """

    host_address: str
    port_number: int

    def __init__(
        self,
        host_address: str = DEFAULT_ESCL_IP,
        port_number: int = DEFAULT_ESCL_PORT,
    ) -> None:
        """
        Initialize the wireless eSCL scanner client.

        Parameters
        ----------
        host_address : str, optional
            IPv4 address or hostname of the scanner, by default ``DEFAULT_ESCL_IP``.
        port_number : int, optional
            HTTP TCP port of the eSCL service, by default ``DEFAULT_ESCL_PORT``.

        Returns
        -------
        None
        """
        self.host_address = host_address
        self.port_number = port_number

    @property
    def base_url(self) -> str:
        """
        Return the root ``/eSCL`` endpoint URL.

        Returns
        -------
        str
            Formatted HTTP base URL.
        """
        endpoint_url: str = f"http://{self.host_address}:{self.port_number}/eSCL"
        return endpoint_url

    def is_reachable(self, probe_timeout_seconds: float = 5.0) -> bool:
        """
        Check whether the remote eSCL scanner responds with HTTP 200 on ``/ScannerStatus``.

        Parameters
        ----------
        probe_timeout_seconds : float, optional
            Socket connection timeout in seconds, by default ``5.0``.

        Returns
        -------
        bool
            ``True`` when the scanner endpoint responds with HTTP 200, ``False`` otherwise.
        """
        status_url: str = f"{self.base_url}/ScannerStatus"
        attempt_number: int
        for attempt_number in range(2):
            try:
                with urllib.request.urlopen(status_url, timeout=probe_timeout_seconds) as response:
                    is_http_ok: bool = int(response.status) == 200
                    if is_http_ok:
                        return True
            except Exception:
                if attempt_number == 0:
                    time.sleep(0.5)
        return False

    def wait_until_idle(self, timeout_seconds: float = 25.0) -> bool:
        """
        Poll ``/ScannerStatus`` until ``<pwg:State>Idle</pwg:State>`` is reported or timeout expires.

        Parameters
        ----------
        timeout_seconds : float, optional
            Maximum time in seconds to wait for the carriage to return to ``Idle``,
            by default ``25.0``.

        Returns
        -------
        bool
            ``True`` if the scanner reported ``Idle`` within the timeout window, ``False`` otherwise.
        """
        status_url: str = f"{self.base_url}/ScannerStatus"
        deadline_timestamp: float = time.time() + timeout_seconds
        while time.time() < deadline_timestamp:
            try:
                with urllib.request.urlopen(status_url, timeout=3.0) as status_response:
                    status_xml_text: str = status_response.read().decode("utf-8", errors="ignore")
                    if "<pwg:State>Idle</pwg:State>" in status_xml_text:
                        return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    def query_capabilities(self, timeout_seconds: float = 6.0) -> str:
        """
        Fetch the raw ``/ScannerCapabilities`` XML document from the scanner.

        Parameters
        ----------
        timeout_seconds : float, optional
            HTTP request timeout in seconds, by default ``6.0``.

        Returns
        -------
        str
            UTF-8 decoded eSCL capabilities XML payload.

        Raises
        ------
        ConnectionError
            If the HTTP request fails or times out.
        """
        capabilities_url: str = f"{self.base_url}/ScannerCapabilities"
        try:
            with urllib.request.urlopen(capabilities_url, timeout=timeout_seconds) as response:
                xml_payload: str = response.read().decode("utf-8")
                return xml_payload
        except Exception as error_message:
            raise ConnectionError(
                f"Failed to query eSCL capabilities: {error_message}"
            ) from error_message

    def scan(
        self,
        output_file_path: Path,
        resolution_dpi: int = 300,
        half_area: bool = False,
        scan_width_inches: float = 8.5,
        scan_height_inches: float = 11.69,
        intent_type: str = "Document",
        offset_x_inches: float = 0.0,
        offset_y_inches: float = 0.0,
        color_mode: str = "color",
        brightness: int = 0,
        contrast: int = 0,
        rotation_degrees: int = 0,
        auto_crop_whitespace: bool = False,
        output_format: str = "png",
        jpeg_quality: int = 95,
        enable_beep: bool = True,
        resolved_region: Optional[ResolvedScanRegion] = None,
    ) -> Path:
        """
        Execute a wireless eSCL flatbed scan with deterministic software clipping and export.

        Parameters
        ----------
        output_file_path : Path
            Destination path where the acquired scan will be saved.
        resolution_dpi : int, optional
            Optical scan resolution in dots per inch, by default ``300``.
        half_area : bool, optional
            Legacy flag restricting capture height to 50 percent, by default ``False``.
        scan_width_inches : float, optional
            Capture width in inches when ``resolved_region`` is omitted, by default ``8.5``.
        scan_height_inches : float, optional
            Capture height in inches when ``resolved_region`` is omitted, by default ``11.69``.
        intent_type : str, optional
            Scan intent name (``"Document"``, ``"Photo"``, ``"TextAndGraphic"``, ``"Preview"``),
            by default ``"Document"``.
        offset_x_inches : float, optional
            Horizontal origin offset in inches, by default ``0.0``.
        offset_y_inches : float, optional
            Vertical origin offset in inches, by default ``0.0``.
        color_mode : str, optional
            Target color mode (``"color"``, ``"grayscale"``, or ``"bw"``), by default ``"color"``.
        brightness : int, optional
            Relative brightness adjustment in ``[-100, 100]``, by default ``0``.
        contrast : int, optional
            Relative contrast adjustment in ``[-100, 100]``, by default ``0``.
        rotation_degrees : int, optional
            Clockwise post-scan rotation angle in ``{0, 90, 180, 270}``, by default ``0``.
        auto_crop_whitespace : bool, optional
            Trim uniform white borders when ``True``, by default ``False``.
        output_format : str, optional
            Encoded output format (``"png"``, ``"jpg"``, ``"tiff"``, ``"bmp"``, ``"pdf"``),
            by default ``"png"``.
        jpeg_quality : int, optional
            JPEG encoding quality in ``[1, 100]``, by default ``95``.
        enable_beep : bool, optional
            Play acoustic completion notification when ``True``, by default ``True``.
        resolved_region : Optional[ResolvedScanRegion], optional
            Pre-resolved physical region overriding ``scan_width_inches`` / ``scan_height_inches``,
            by default ``None``.

        Returns
        -------
        Path
            Path to the written scan file.

        Raises
        ------
        ConnectionError
            If the wireless scanner is unreachable.
        RuntimeError
            If scan job creation or image decoding fails.
        TimeoutError
            If payload retrieval exceeds the optical scan timeout window.
        """
        if not self.is_reachable():
            raise ConnectionError(
                f"Cannot reach eSCL scanner at {self.host_address}:{self.port_number}."
            )

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        active_region: ResolvedScanRegion
        if resolved_region is not None:
            active_region = resolved_region
        else:
            effective_height_inches: float = (
                scan_height_inches / 2.0 if half_area else scan_height_inches
            )
            is_default_full_bed: bool = (
                not half_area
                and offset_x_inches <= 0.002
                and offset_y_inches <= 0.002
                and abs(scan_width_inches - PLATEN_MAX_WIDTH_INCHES) <= 0.02
                and abs(effective_height_inches - PLATEN_MAX_HEIGHT_INCHES) <= 0.02
            )
            if is_default_full_bed:
                active_region = resolve_scan_region(paper_size="full")
            else:
                active_region = resolve_scan_region(
                    paper_size="custom",
                    custom_width=scan_width_inches,
                    custom_height=effective_height_inches,
                    offset_x=offset_x_inches,
                    offset_y=offset_y_inches,
                    measurement_unit="in",
                )

        escl_intent_token: str = ESCL_INTENT_MAPPING.get(
            intent_type.strip().lower(),
            intent_type if intent_type in ("Document", "Photo", "TextAndGraphic", "Preview") else "Document",
        )
        escl_color_token: str = ESCL_COLOR_MODE_MAPPING.get(
            color_mode.strip().lower(),
            "RGB24",
        )

        clamped_brightness: int = max(-100, min(100, brightness))
        clamped_contrast: int = max(-100, min(100, contrast))
        escl_brightness_value: int = max(0, min(2000, 1000 + (clamped_brightness * 10)))
        escl_contrast_value: int = max(0, min(2000, 1000 + (clamped_contrast * 10)))

        tone_xml_lines: str = ""
        if clamped_brightness != 0 or clamped_contrast != 0:
            tone_xml_lines = (
                f"  <scan:Brightness>{escl_brightness_value}</scan:Brightness>\n"
                f"  <scan:Contrast>{escl_contrast_value}</scan:Contrast>\n"
            )

        normalized_output_format: str = output_format.strip().lower().lstrip(".")
        escl_document_format: str = (
            "application/pdf" if normalized_output_format == "pdf" else "image/jpeg"
        )

        self.wait_until_idle(timeout_seconds=25.0)

        scan_xml_payload: str = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<scan:ScanSettings xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm" '
            'xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03">\n'
            "  <pwg:Version>2.63</pwg:Version>\n"
            f"  <scan:Intent>{escl_intent_token}</scan:Intent>\n"
            "  <pwg:ScanRegions>\n"
            "    <pwg:ScanRegion>\n"
            "      <pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>\n"
            f"      <pwg:XOffset>{active_region.offset_x_escl_units}</pwg:XOffset>\n"
            f"      <pwg:YOffset>{active_region.offset_y_escl_units}</pwg:YOffset>\n"
            f"      <pwg:Width>{active_region.width_escl_units}</pwg:Width>\n"
            f"      <pwg:Height>{active_region.height_escl_units}</pwg:Height>\n"
            "    </pwg:ScanRegion>\n"
            "  </pwg:ScanRegions>\n"
            "  <pwg:InputSource>Platen</pwg:InputSource>\n"
            f"  <scan:DocumentFormatExt>{escl_document_format}</scan:DocumentFormatExt>\n"
            f"  <scan:XResolution>{resolution_dpi}</scan:XResolution>\n"
            f"  <scan:YResolution>{resolution_dpi}</scan:YResolution>\n"
            f"  <scan:ColorMode>{escl_color_token}</scan:ColorMode>\n"
            f"{tone_xml_lines}"
            "</scan:ScanSettings>\n"
        )

        jobs_url: str = f"{self.base_url}/ScanJobs"
        request_object: urllib.request.Request = urllib.request.Request(
            jobs_url,
            data=scan_xml_payload.encode("utf-8"),
            headers={"Content-Type": "text/xml"},
            method="POST",
        )

        location_header: Optional[str] = None
        maximum_job_creation_attempts: int = 5
        for attempt_index in range(maximum_job_creation_attempts):
            try:
                with urllib.request.urlopen(request_object, timeout=15) as job_response:
                    location_header = job_response.headers.get("Location")
                    if location_header:
                        break
            except urllib.error.HTTPError as http_error:
                if http_error.code == 503 and attempt_index < maximum_job_creation_attempts - 1:
                    print(
                        f"  [Notice] Scanner carriage busy (HTTP 503). Retrying in 2.5s "
                        f"(attempt {attempt_index + 1}/{maximum_job_creation_attempts})..."
                    )
                    time.sleep(2.5)
                    continue
                raise

        if not location_header:
            raise RuntimeError("eSCL scanner did not return a valid ScanJob Location header.")

        job_url: str = location_header
        if not job_url.startswith("http"):
            job_url = f"http://{self.host_address}:{self.port_number}{location_header}"

        document_url: str = f"{job_url}/NextDocument"
        timeout_limit_seconds: int = 240 if resolution_dpi > 300 else 60
        document_request: urllib.request.Request = urllib.request.Request(document_url)

        document_data: Optional[bytes] = None
        content_type: str = ""
        start_timestamp: float = time.time()

        while time.time() - start_timestamp < float(timeout_limit_seconds):
            try:
                with urllib.request.urlopen(
                    document_request,
                    timeout=float(timeout_limit_seconds),
                ) as document_response:
                    document_data = document_response.read()
                    content_type = str(document_response.headers.get("Content-Type", ""))
                    break
            except urllib.error.HTTPError as http_error:
                if http_error.code in (404, 503):
                    time.sleep(1.5)
                    continue
                raise
            except Exception:
                time.sleep(1.5)
                continue

        if not document_data:
            raise TimeoutError(f"Timed out waiting for scan payload from {document_url}")

        clipped_bgr_image: np.ndarray = decode_and_clip_escl_payload(
            document_data=document_data,
            content_type=content_type,
            resolution_dpi=resolution_dpi,
            resolved_region=active_region,
        )

        saved_path: Path = apply_post_scan_adjustments_and_save(
            source_bgr_image=clipped_bgr_image,
            output_file_path=output_file_path,
            resolution_dpi=resolution_dpi,
            color_mode=color_mode,
            brightness=clamped_brightness,
            contrast=clamped_contrast,
            rotation_degrees=rotation_degrees,
            auto_crop_whitespace=auto_crop_whitespace,
            output_format=output_format,
            jpeg_quality=jpeg_quality,
            apply_software_tone=False,
        )

        if enable_beep:
            play_completion_beep()

        return saved_path


def discover_network_escl_scanners(
    primary_host: str = DEFAULT_ESCL_IP,
    primary_port: int = DEFAULT_ESCL_PORT,
    timeout_seconds: float = 2.5,
) -> list[dict[str, object]]:
    """
    Discover active wireless eSCL network scanners across the local subnet.

    Parameters
    ----------
    primary_host : str, optional
        Primary candidate IPv4 address or hostname, by default ``DEFAULT_ESCL_IP``.
    primary_port : int, optional
        Primary candidate HTTP TCP port, by default ``DEFAULT_ESCL_PORT``.
    timeout_seconds : float, optional
        Probe timeout per candidate endpoint in seconds, by default ``2.5``.

    Returns
    -------
    list[dict[str, object]]
        List of discovered eSCL scanner descriptors.
    """
    discovered_endpoints: list[dict[str, object]] = []
    seen_host_addresses: set[str] = set()

    candidate_endpoints: list[tuple[str, int]] = [(primary_host, primary_port)]
    if primary_port != 80:
        candidate_endpoints.append((primary_host, 80))

    try:
        arp_process: subprocess.CompletedProcess[str] = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        arp_output_text: str = arp_process.stdout
        matched_ipv4_addresses: list[str] = re.findall(
            r"((?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d+\.\d+)",
            arp_output_text,
        )
        candidate_address: str
        for candidate_address in matched_ipv4_addresses:
            last_segment: str = candidate_address.split(".")[-1]
            if last_segment in ("1", "255"):
                continue
            if candidate_address not in seen_host_addresses and candidate_address != primary_host:
                candidate_endpoints.append((candidate_address, 8080))
                candidate_endpoints.append((candidate_address, 80))
    except Exception:
        pass

    endpoint_tuple: tuple[str, int]
    for endpoint_tuple in candidate_endpoints:
        candidate_host: str = endpoint_tuple[0]
        candidate_port: int = endpoint_tuple[1]
        host_port_key: str = f"{candidate_host}:{candidate_port}"
        if host_port_key in seen_host_addresses:
            continue
        seen_host_addresses.add(host_port_key)

        socket_probe: Optional[socket.socket] = None
        is_port_open: bool = False
        try:
            socket_probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_probe.settimeout(0.35 if candidate_host != primary_host else 1.0)
            socket_result: int = socket_probe.connect_ex((candidate_host, candidate_port))
            is_port_open = (socket_result == 0)
        except Exception:
            is_port_open = False
        finally:
            if socket_probe is not None:
                try:
                    socket_probe.close()
                except Exception:
                    pass

        if not is_port_open:
            continue

        probe_client: EsclClient = EsclClient(host_address=candidate_host, port_number=candidate_port)
        if not probe_client.is_reachable(probe_timeout_seconds=0.8):
            continue

        friendly_name: str = "Wireless Network Scanner"
        unique_device_identifier: str = f"escl:{candidate_host}_{candidate_port}"

        try:
            capabilities_xml_text: str = probe_client.query_capabilities(timeout_seconds=1.2)
            model_match: Optional[re.Match[str]] = re.search(
                r"<pwg:MakeAndModel>(.*?)</pwg:MakeAndModel>",
                capabilities_xml_text,
            )
            if model_match is not None:
                parsed_model_name: str = model_match.group(1).strip()
                if parsed_model_name and parsed_model_name.lower() not in ("xxxx", "unknown"):
                    friendly_name = parsed_model_name
                elif parsed_model_name.lower() == "xxxx":
                    friendly_name = "HP DeskJet Wireless Scanner"

            uuid_match: Optional[re.Match[str]] = re.search(
                r"<scan:UUID>(.*?)</scan:UUID>",
                capabilities_xml_text,
            )
            if uuid_match is not None:
                extracted_uuid: str = uuid_match.group(1).strip()
                if extracted_uuid:
                    unique_device_identifier = f"escl:{extracted_uuid}"
        except Exception:
            pass

        descriptor: dict[str, object] = {
            "id": unique_device_identifier,
            "name": friendly_name,
            "transport": "wifi",
            "host": candidate_host,
            "port": candidate_port,
            "device_id": "",
            "reachable": True,
        }
        discovered_endpoints.append(descriptor)

    return discovered_endpoints

