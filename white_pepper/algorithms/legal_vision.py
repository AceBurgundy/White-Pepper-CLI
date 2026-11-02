"""Deterministic two-pass legal paper computer vision stitcher.

Stitches two Letter-clamped scans (top upright pass and bottom upside-down pass)
into a single high-fidelity, zero-gradient US Legal (8.50" x 14.00") document.
"""

# DPI = Dots Per Inch
# PDF = Portable Document Format
# BGR = Blue Green Red
# RGB = Red Green Blue
# ANSI = American National Standards Institute
# NCC = Normalized Cross Correlation

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from white_pepper.algorithms.geometry import (
    millimeters_to_pixels,
)

# Standard ANSI paper dimensions in inches and millimeters
LEGAL_PAPER_WIDTH_INCHES: float = 8.50
LEGAL_PAPER_HEIGHT_INCHES: float = 14.00
LETTER_PAPER_HEIGHT_INCHES: float = 11.00
OVERLAP_REGION_HEIGHT_INCHES: float = LETTER_PAPER_HEIGHT_INCHES - (
    LEGAL_PAPER_HEIGHT_INCHES - LETTER_PAPER_HEIGHT_INCHES
)  # 11.00 - 3.00 = 8.00 inches


@dataclass(frozen=True)
class LegalStitchResult:
    """Immutable data contract encapsulating two-pass legal stitching results.

    Attributes
    ----------
    stitched_bgr_image : np.ndarray
        Final stitched composite BGR image representing the full 8.50" x 14.00" legal document.
    horizontal_offset_pixels : float
        Detected horizontal placement shift between pass 1 and pass 2 in pixels.
    vertical_offset_pixels : float
        Detected vertical placement shift in pixels from phase correlation.
    correlation_confidence : float
        Phase correlation confidence score between 0.0 and 1.0.
    seam_vertical_coordinate_pixels : int
        Vertical pixel index where the two passes were conjoined.
    resolution_dpi : int
        Optical resolution in dots per inch.
    """

    stitched_bgr_image: np.ndarray
    horizontal_offset_pixels: float
    vertical_offset_pixels: float
    correlation_confidence: float
    seam_vertical_coordinate_pixels: int
    resolution_dpi: int


def calculate_legal_dimensions_pixels(resolution_dpi: int) -> Tuple[int, int]:
    """Calculate standard US Legal document dimensions in pixels for a given DPI.

    Parameters
    ----------
    resolution_dpi : int
        Optical resolution in dots per inch.

    Returns
    -------
    Tuple[int, int]
        Tuple of (width_pixels, height_pixels).
    """
    width_pixels: int = round(LEGAL_PAPER_WIDTH_INCHES * float(resolution_dpi))
    height_pixels: int = round(LEGAL_PAPER_HEIGHT_INCHES * float(resolution_dpi))
    return width_pixels, height_pixels


def stitch_legal_two_pass(
    pass1_top_bgr_image: np.ndarray,
    pass2_bottom_upside_down_bgr_image: np.ndarray,
    resolution_dpi: int = 300,
    enable_phase_correlation: bool = True,
    correlation_threshold: float = 0.50,
) -> LegalStitchResult:
    """Stitch top upright and bottom upside-down Letter scans into a seamless Legal sheet.

    Parameters
    ----------
    pass1_top_bgr_image : np.ndarray
        BGR image of the top scan (paper upright, clamped to Letter 8.50" x 11.00").
    pass2_bottom_upside_down_bgr_image : np.ndarray
        BGR image of the bottom scan (paper upside-down, clamped to Letter 8.50" x 11.00").
    resolution_dpi : int, optional
        Optical resolution in dots per inch, by default 300.
    enable_phase_correlation : bool, optional
        Whether to refine registration using Fourier Phase Correlation, by default True.
    correlation_threshold : float, optional
        Minimum phase correlation peak response required to accept sub-pixel registration,
        by default 0.50.

    Returns
    -------
    LegalStitchResult
        Result contract containing composite image, offsets, and seam details.

    Raises
    ------
    ValueError
        If input images are empty or have invalid dimensions.
    """
    if pass1_top_bgr_image is None or pass1_top_bgr_image.size == 0:
        raise ValueError("Pass 1 top image cannot be None or empty.")
    if pass2_bottom_upside_down_bgr_image is None or pass2_bottom_upside_down_bgr_image.size == 0:
        raise ValueError("Pass 2 bottom image cannot be None or empty.")

    pass1_height_pixels: int = pass1_top_bgr_image.shape[0]
    pass1_width_pixels: int = pass1_top_bgr_image.shape[1]

    # Step 1: Rotate Pass 2 by 180 degrees to restore upright orientation
    # Rotating 180 degrees flips both vertically and horizontally
    pass2_upright_bgr_image: np.ndarray = cv2.rotate(
        pass2_bottom_upside_down_bgr_image, cv2.ROTATE_180
    )
    pass2_height_pixels: int = pass2_upright_bgr_image.shape[0]
    pass2_width_pixels: int = pass2_upright_bgr_image.shape[1]

    # Ensure widths match exactly
    common_width_pixels: int = min(pass1_width_pixels, pass2_width_pixels)
    pass1_aligned: np.ndarray = pass1_top_bgr_image[:, :common_width_pixels]
    pass2_aligned: np.ndarray = pass2_upright_bgr_image[:, :common_width_pixels]

    # Theoretical overlap height in pixels: 8.00 inches
    overlap_height_pixels: int = round(OVERLAP_REGION_HEIGHT_INCHES * float(resolution_dpi))
    overlap_height_pixels = min(overlap_height_pixels, pass1_height_pixels, pass2_height_pixels)

    horizontal_offset_pixels: float = 0.0
    vertical_offset_pixels: float = 0.0
    correlation_confidence: float = 0.0

    # Step 2: Phase correlation in the 8.00" overlap zone
    if enable_phase_correlation and overlap_height_pixels > 100:
        # Extract overlap bands:
        # Band 1: Bottom 8.00" of Pass 1
        pass1_overlap_band: np.ndarray = pass1_aligned[
            pass1_height_pixels - overlap_height_pixels : pass1_height_pixels, :
        ]
        # Band 2: Top 8.00" of upright Pass 2
        pass2_overlap_band: np.ndarray = pass2_aligned[:overlap_height_pixels, :]

        # Convert to single-channel float32
        pass1_grayscale: np.ndarray = cv2.cvtColor(pass1_overlap_band, cv2.COLOR_BGR2GRAY).astype(
            np.float32
        )
        pass2_grayscale: np.ndarray = cv2.cvtColor(pass2_overlap_band, cv2.COLOR_BGR2GRAY).astype(
            np.float32
        )

        # Apply Hanning window to prevent edge spectral leakage
        hanning_window: np.ndarray = cv2.createHanningWindow(
            (pass1_grayscale.shape[1], pass1_grayscale.shape[0]), cv2.CV_32F
        )

        detected_shift, response_confidence = cv2.phaseCorrelate(
            pass1_grayscale, pass2_grayscale, hanning_window
        )

        correlation_confidence = float(response_confidence)
        if correlation_confidence >= correlation_threshold:
            horizontal_offset_pixels = float(detected_shift[0])
            vertical_offset_pixels = float(detected_shift[1])

            # Safety clamp: Physical paper placement shift should not exceed 10mm (~120px @ 300 DPI)
            maximum_shift_allowance_pixels: float = float(resolution_dpi) * 0.40
            if (
                abs(horizontal_offset_pixels) > maximum_shift_allowance_pixels
                or abs(vertical_offset_pixels) > maximum_shift_allowance_pixels
            ):
                # Discard erratic correlation
                horizontal_offset_pixels = 0.0
                vertical_offset_pixels = 0.0
                correlation_confidence = 0.0

    # Step 3: Deterministic cutting and concatenation
    # In upright Pass 2, the non-redundant tail starts at the end of the overlap:
    # slice_start_vertical = overlap_height_pixels + vertical_offset_pixels
    tail_slice_start_vertical: int = int(
        round(float(overlap_height_pixels) + vertical_offset_pixels)
    )
    tail_slice_start_vertical = max(0, min(tail_slice_start_vertical, pass2_height_pixels - 1))

    tail_slice_bgr: np.ndarray = pass2_aligned[tail_slice_start_vertical:, :]

    # Apply horizontal translation if detected
    if abs(horizontal_offset_pixels) >= 1.0:
        translation_matrix: np.ndarray = np.array(
            [[1.0, 0.0, -horizontal_offset_pixels], [0.0, 1.0, 0.0]], dtype=np.float32
        )
        tail_slice_bgr = cv2.warpAffine(
            tail_slice_bgr,
            translation_matrix,
            (tail_slice_bgr.shape[1], tail_slice_bgr.shape[0]),
            borderMode=cv2.BORDER_REPLICATE,
        )

    # Concat Pass 1 (top 11.00") with the tail slice (remaining 3.00")
    stitched_composite_bgr: np.ndarray = np.vstack([pass1_aligned, tail_slice_bgr])

    # Target legal dimensions
    target_legal_width, target_legal_height = calculate_legal_dimensions_pixels(resolution_dpi)

    # Normalize final composite to target legal dimensions
    current_composite_height: int = stitched_composite_bgr.shape[0]
    current_composite_width: int = stitched_composite_bgr.shape[1]

    if current_composite_height > target_legal_height:
        stitched_composite_bgr = stitched_composite_bgr[:target_legal_height, :]
    elif current_composite_height < target_legal_height:
        vertical_padding_needed: int = target_legal_height - current_composite_height
        bottom_padding: np.ndarray = np.full(
            (vertical_padding_needed, current_composite_width, 3), 255, dtype=np.uint8
        )
        stitched_composite_bgr = np.vstack([stitched_composite_bgr, bottom_padding])

    if stitched_composite_bgr.shape[1] != target_legal_width:
        stitched_composite_bgr = cv2.resize(
            stitched_composite_bgr,
            (target_legal_width, target_legal_height),
            interpolation=cv2.INTER_LANCZOS4,
        )

    return LegalStitchResult(
        stitched_bgr_image=stitched_composite_bgr,
        horizontal_offset_pixels=horizontal_offset_pixels,
        vertical_offset_pixels=vertical_offset_pixels,
        correlation_confidence=correlation_confidence,
        seam_vertical_coordinate_pixels=pass1_height_pixels,
        resolution_dpi=resolution_dpi,
    )


def save_legal_stitch_result_to_pdf(
    stitch_result: LegalStitchResult,
    target_pdf_path: Path,
) -> Path:
    """Save the stitched legal document to a high-resolution PDF with 1:1 scaling.

    Parameters
    ----------
    stitch_result : LegalStitchResult
        Result containing the stitched composite BGR image.
    target_pdf_path : Path
        Destination path for the resulting PDF.

    Returns
    -------
    Path
        Destination path to the saved PDF file.
    """
    rgb_composite: np.ndarray = cv2.cvtColor(
        stitch_result.stitched_bgr_image, cv2.COLOR_BGR2RGB
    )
    pil_image: Image.Image = Image.fromarray(rgb_composite)

    target_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pil_image.save(
        target_pdf_path,
        "PDF",
        resolution=float(stitch_result.resolution_dpi),
    )
    return target_pdf_path
