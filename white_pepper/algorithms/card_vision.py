"""
Mathematical card contour analysis, 1D edge pinning, rounded-corner alpha masking, and compositing.
"""

from __future__ import annotations

# DPI = Dots Per Inch
# ID-1 = Identification Card Format 1 (ISO/IEC 7810)
# RGB = Red Green Blue
# BGR = Blue Green Red

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from white_pepper.algorithms.geometry import (
    ID1_CORNER_RADIUS_MILLIMETERS,
    ID1_HEIGHT_MILLIMETERS,
    ID1_WIDTH_MILLIMETERS,
    millimeters_to_pixels,
)


@dataclass
class CardExtractionResult:
    """
    Structured output returned by ISO/IEC 7810 ID-1 card extraction and deskewing.

    Attributes
    ----------
    extracted_image : np.ndarray
        Deskewed 4-channel BGRA card image with anti-aliased rounded-corner alpha mask.
    rotation_angle_degrees : float
        Detected rotational skew angle in degrees corrected during extraction.
    target_width_pixels : int
        Width of ``extracted_image`` in pixels at the requested DPI.
    target_height_pixels : int
        Height of ``extracted_image`` in pixels at the requested DPI.
    confidence_score : float
        Area-normalized contour match score in ``[0.0, 1.0]``.
    """

    extracted_image: np.ndarray
    rotation_angle_degrees: float
    target_width_pixels: int
    target_height_pixels: int
    confidence_score: float


def create_rounded_corner_mask(
    image_width: int,
    image_height: int,
    corner_radius_pixels: int,
) -> np.ndarray:
    """
    Generate a 4x supersampled, anti-aliased rounded-rectangle alpha mask.

    Parameters
    ----------
    image_width : int
        Target mask width in pixels.
    image_height : int
        Target mask height in pixels.
    corner_radius_pixels : int
        Corner fillet radius in pixels (``0`` produces a solid rectangular mask).

    Returns
    -------
    np.ndarray
        Single-channel ``uint8`` alpha mask of shape ``(image_height, image_width)``.
    """
    if corner_radius_pixels <= 0:
        solid_mask: np.ndarray = np.full((image_height, image_width), 255, dtype=np.uint8)
        return solid_mask

    clamped_radius: int = min(corner_radius_pixels, image_width // 2, image_height // 2)
    upscale_factor: int = 4
    supersampled_width: int = image_width * upscale_factor
    supersampled_height: int = image_height * upscale_factor
    supersampled_radius: int = clamped_radius * upscale_factor

    mask_supersampled: np.ndarray = np.zeros(
        (supersampled_height, supersampled_width),
        dtype=np.uint8,
    )

    cv2.rectangle(
        mask_supersampled,
        (supersampled_radius, 0),
        (supersampled_width - supersampled_radius, supersampled_height),
        255,
        thickness=-1,
    )
    cv2.rectangle(
        mask_supersampled,
        (0, supersampled_radius),
        (supersampled_width, supersampled_height - supersampled_radius),
        255,
        thickness=-1,
    )

    center_coordinates: list[tuple[int, int]] = [
        (supersampled_radius, supersampled_radius),
        (supersampled_width - supersampled_radius, supersampled_radius),
        (supersampled_radius, supersampled_height - supersampled_radius),
        (supersampled_width - supersampled_radius, supersampled_height - supersampled_radius),
    ]

    corner_point: tuple[int, int]
    for corner_point in center_coordinates:
        corner_horizontal_center: int = corner_point[0]
        corner_vertical_center: int = corner_point[1]
        cv2.circle(
            mask_supersampled,
            (corner_horizontal_center, corner_vertical_center),
            supersampled_radius,
            255,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )

    antialiased_mask: np.ndarray = cv2.resize(
        mask_supersampled,
        (image_width, image_height),
        interpolation=cv2.INTER_AREA,
    )
    return antialiased_mask


def composite_card_onto_background(
    card_bgra_image: np.ndarray,
    background_mode: str = "white",
) -> np.ndarray:
    """
    Composite a 4-channel BGRA card image onto a solid RGB background or retain transparency.

    Parameters
    ----------
    card_bgra_image : np.ndarray
        Extracted 4-channel BGRA (or 3-channel BGR) card image.
    background_mode : str, optional
        Background style (``"transparent"``, ``"white"``, or ``"black"``), by default ``"white"``.

    Returns
    -------
    np.ndarray
        4-channel BGRA image when ``background_mode == "transparent"``, otherwise a 3-channel
        BGR image composited over white or black.
    """
    normalized_background: str = background_mode.strip().lower()
    if normalized_background == "transparent":
        return card_bgra_image

    if len(card_bgra_image.shape) < 3 or card_bgra_image.shape[2] < 4:
        return card_bgra_image

    fill_intensity: int = 0 if normalized_background == "black" else 255
    bgr_foreground: np.ndarray = card_bgra_image[:, :, :3].astype(np.float32)
    alpha_channel: np.ndarray = (card_bgra_image[:, :, 3:4].astype(np.float32)) / 255.0
    solid_canvas: np.ndarray = np.full_like(bgr_foreground, float(fill_intensity))

    blended_float: np.ndarray = (bgr_foreground * alpha_channel) + (
        solid_canvas * (1.0 - alpha_channel)
    )
    composited_bgr: np.ndarray = np.clip(blended_float, 0.0, 255.0).astype(np.uint8)
    return composited_bgr


def extract_and_deskew_id_card(
    source_image: np.ndarray,
    resolution_dpi: int = 300,
    safety_inset_millimeters: float = 0.5,
    corner_radius_millimeters: float = ID1_CORNER_RADIUS_MILLIMETERS,
) -> Optional[CardExtractionResult]:
    """
    Isolate, rotationally deskew, crop, and alpha-mask an ID-1 card from a raw platen scan.

    Parameters
    ----------
    source_image : np.ndarray
        Input 3-channel BGR scan containing an ID-1 card against the scanner background.
    resolution_dpi : int, optional
        Optical scan resolution in dots per inch, by default ``300``.
    safety_inset_millimeters : float, optional
        Edge safety inset in millimeters trimmed prior to resizing to remove border halo,
        by default ``0.5``.
    corner_radius_millimeters : float, optional
        Rounded corner fillet radius in millimeters, by default ``ID1_CORNER_RADIUS_MILLIMETERS``
        (``3.18`` mm).

    Returns
    -------
    Optional[CardExtractionResult]
        Structured extraction result containing the 4-channel BGRA card, or ``None`` if no
        contour matching ID-1 card geometry could be isolated.
    """
    if source_image is None or source_image.size == 0:
        return None

    target_width_pixels: int = millimeters_to_pixels(ID1_WIDTH_MILLIMETERS, resolution_dpi)
    target_height_pixels: int = millimeters_to_pixels(ID1_HEIGHT_MILLIMETERS, resolution_dpi)
    corner_radius_pixels: int = max(
        0,
        millimeters_to_pixels(max(0.0, corner_radius_millimeters), resolution_dpi),
    )
    safety_inset_pixels: int = max(
        0,
        millimeters_to_pixels(max(0.0, safety_inset_millimeters), resolution_dpi),
    )

    working_scale: float = 0.25
    working_width: int = max(1, int(round(float(source_image.shape[1]) * working_scale)))
    working_height: int = max(1, int(round(float(source_image.shape[0]) * working_scale)))
    working_image: np.ndarray = cv2.resize(source_image, (working_width, working_height))

    grayscale_image: np.ndarray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
    blurred_image: np.ndarray = cv2.GaussianBlur(grayscale_image, (7, 7), 0)

    threshold_pair: tuple[float, np.ndarray] = cv2.threshold(
        blurred_image,
        0.0,
        255.0,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    binary_mask: np.ndarray = threshold_pair[1]

    structuring_element: np.ndarray = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed_mask: np.ndarray = cv2.morphologyEx(
        binary_mask,
        cv2.MORPH_CLOSE,
        structuring_element,
        iterations=2,
    )

    contours_tuple: tuple[tuple[np.ndarray, ...], Optional[np.ndarray]] = cv2.findContours(
        closed_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    contours: tuple[np.ndarray, ...] = contours_tuple[0]
    if not contours:
        return None

    expected_area_working: float = (
        float(target_width_pixels * target_height_pixels) * (working_scale**2)
    )
    minimum_allowed_area: float = expected_area_working * 0.45

    candidate_contours: list[np.ndarray] = [
        contour for contour in contours if cv2.contourArea(contour) >= minimum_allowed_area
    ]

    if not candidate_contours:
        return None

    largest_contour: np.ndarray = max(candidate_contours, key=cv2.contourArea)
    rotated_bounding_box: tuple[tuple[float, float], tuple[float, float], float] = cv2.minAreaRect(
        largest_contour
    )
    box_center: tuple[float, float] = rotated_bounding_box[0]
    box_dimensions: tuple[float, float] = rotated_bounding_box[1]
    box_angle: float = float(rotated_bounding_box[2])

    bounding_box_horizontal_center: float = float(box_center[0])
    bounding_box_vertical_center: float = float(box_center[1])
    box_width: float = float(box_dimensions[0])
    box_height: float = float(box_dimensions[1])

    scale_multiplier: float = 1.0 / working_scale
    full_horizontal_center: float = bounding_box_horizontal_center * scale_multiplier
    full_vertical_center: float = bounding_box_vertical_center * scale_multiplier
    full_width: float = box_width * scale_multiplier
    full_height: float = box_height * scale_multiplier

    if full_width < full_height:
        swapped_width: float = full_height
        swapped_height: float = full_width
        full_width = swapped_width
        full_height = swapped_height
        box_angle = box_angle + 90.0

    rotation_matrix: np.ndarray = cv2.getRotationMatrix2D(
        (full_horizontal_center, full_vertical_center),
        box_angle,
        1.0,
    )

    rotated_source: np.ndarray = cv2.warpAffine(
        source_image,
        rotation_matrix,
        (int(source_image.shape[1]), int(source_image.shape[0])),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    inset_crop_width: int = max(16, target_width_pixels - (2 * safety_inset_pixels))
    inset_crop_height: int = max(16, target_height_pixels - (2 * safety_inset_pixels))
    half_width: float = float(inset_crop_width) / 2.0
    half_height: float = float(inset_crop_height) / 2.0

    horizontal_start: int = max(0, int(round(full_horizontal_center - half_width)))
    vertical_start: int = max(0, int(round(full_vertical_center - half_height)))
    horizontal_end: int = min(int(rotated_source.shape[1]), horizontal_start + inset_crop_width)
    vertical_end: int = min(int(rotated_source.shape[0]), vertical_start + inset_crop_height)

    cropped_card_bgr: np.ndarray = rotated_source[vertical_start:vertical_end, horizontal_start:horizontal_end]
    if (
        int(cropped_card_bgr.shape[0]) != target_height_pixels
        or int(cropped_card_bgr.shape[1]) != target_width_pixels
    ):
        cropped_card_bgr = cv2.resize(
            cropped_card_bgr,
            (target_width_pixels, target_height_pixels),
            interpolation=cv2.INTER_LANCZOS4,
        )

    alpha_mask: np.ndarray = create_rounded_corner_mask(
        target_width_pixels,
        target_height_pixels,
        corner_radius_pixels,
    )

    split_channels: tuple[np.ndarray, ...] = cv2.split(cropped_card_bgr)
    blue_channel: np.ndarray = split_channels[0]
    green_channel: np.ndarray = split_channels[1]
    red_channel: np.ndarray = split_channels[2]
    extracted_card_bgra: np.ndarray = cv2.merge(
        [blue_channel, green_channel, red_channel, alpha_mask]
    )

    confidence: float = min(1.0, float(cv2.contourArea(largest_contour)) / expected_area_working)

    result: CardExtractionResult = CardExtractionResult(
        extracted_image=extracted_card_bgra,
        rotation_angle_degrees=box_angle,
        target_width_pixels=target_width_pixels,
        target_height_pixels=target_height_pixels,
        confidence_score=confidence,
    )
    return result
