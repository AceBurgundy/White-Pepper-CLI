"""
Booklet spread segmentation, dual-page splitting, reading-direction ordering, and bounding analysis.
"""

from __future__ import annotations

# BGR = Blue Green Red
# LTR = Left to Right
# RTL = Right to Left

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np

if TYPE_CHECKING:
    from white_pepper.config import BookletProcessConfiguration


@dataclass
class BookletPageSegment:
    """
    Isolated single-page segment extracted from a raw booklet spread scan.

    Attributes
    ----------
    page_image : np.ndarray
        Cropped BGR image matrix corresponding to the individual booklet page.
    bounding_box : tuple[int, int, int, int]
        Source spread crop rectangle ``(x, y, width, height)`` in pixels.
    page_index_hint : int
        Zero-based reading-order index within the spread (``0`` first, ``1`` second).
    """

    page_image: np.ndarray
    bounding_box: tuple[int, int, int, int]
    page_index_hint: int


def segment_booklet_spread(
    spread_image: np.ndarray,
    split_dual_pages: bool = True,
    margin_padding_pixels: int = 15,
    reading_direction: str = "ltr",
    spread_orientation: str = "landscape",
    spread_aspect_ratio_threshold: float = 1.2,
) -> list[BookletPageSegment]:
    """
    Segment a scanned booklet spread into one or two ordered page crops.

    Parameters
    ----------
    spread_image : np.ndarray
        Input 3-channel BGR booklet spread image.
    split_dual_pages : bool, optional
        Split two-page spreads into left and right pages when ``True``, by default ``True``.
    margin_padding_pixels : int, optional
        Extra pixel margin preserved around detected page contours, by default ``15``.
    reading_direction : str, optional
        Page ordering direction (``"ltr"`` left-to-right or ``"rtl"`` right-to-left),
        by default ``"ltr"``.
    spread_orientation : str, optional
        Layout mode (``"landscape"``, ``"portrait"``, or ``"auto"``), by default ``"landscape"``.
    spread_aspect_ratio_threshold : float, optional
        Minimum width-to-height ratio required to split when ``spread_orientation == "auto"``,
        by default ``1.2``.

    Returns
    -------
    list[BookletPageSegment]
        Ordered list of isolated booklet page segments.
    """
    if spread_image is None or spread_image.size == 0:
        return []

    image_height: int = int(spread_image.shape[0])
    image_width: int = int(spread_image.shape[1])

    normalized_orientation: str = spread_orientation.strip().lower()
    should_split: bool = split_dual_pages
    if normalized_orientation == "portrait":
        should_split = False
    elif normalized_orientation == "auto" and should_split:
        aspect_ratio: float = float(image_width) / float(max(1, image_height))
        if aspect_ratio < spread_aspect_ratio_threshold:
            should_split = False

    if not should_split:
        full_segment: BookletPageSegment = BookletPageSegment(
            page_image=spread_image,
            bounding_box=(0, 0, image_width, image_height),
            page_index_hint=0,
        )
        return [full_segment]

    is_right_to_left: bool = reading_direction.strip().lower() == "rtl"
    safe_padding: int = max(0, margin_padding_pixels)

    downscale_factor: float = 0.25
    scaled_width: int = max(1, int(round(float(image_width) * downscale_factor)))
    scaled_height: int = max(1, int(round(float(image_height) * downscale_factor)))
    scaled_image: np.ndarray = cv2.resize(spread_image, (scaled_width, scaled_height))

    grayscale_image: np.ndarray = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2GRAY)
    blurred_image: np.ndarray = cv2.GaussianBlur(grayscale_image, (5, 5), 0)

    threshold_pair: tuple[float, np.ndarray] = cv2.threshold(
        blurred_image,
        240.0,
        255.0,
        cv2.THRESH_BINARY_INV,
    )
    binary_threshold: np.ndarray = threshold_pair[1]

    contours_tuple: tuple[tuple[np.ndarray, ...], Optional[np.ndarray]] = cv2.findContours(
        binary_threshold,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    contours: tuple[np.ndarray, ...] = contours_tuple[0]
    minimum_page_area_scaled: float = float(scaled_width * scaled_height) * 0.15

    valid_rectangles: list[tuple[int, int, int, int]] = []
    scale_factor: float = 1.0 / downscale_factor

    contour: np.ndarray
    for contour in contours:
        contour_area: float = float(cv2.contourArea(contour))
        if contour_area >= minimum_page_area_scaled:
            detected_bounding_box: tuple[int, int, int, int] = cv2.boundingRect(contour)
            contour_horizontal_start: int = detected_bounding_box[0]
            contour_vertical_start: int = detected_bounding_box[1]
            contour_box_width: int = detected_bounding_box[2]
            contour_box_height: int = detected_bounding_box[3]

            full_horizontal_start: int = max(
                0, int(round(float(contour_horizontal_start) * scale_factor)) - safe_padding
            )
            full_vertical_start: int = max(
                0, int(round(float(contour_vertical_start) * scale_factor)) - safe_padding
            )
            full_width: int = min(
                image_width - full_horizontal_start,
                int(round(float(contour_box_width) * scale_factor)) + (safe_padding * 2),
            )
            full_height: int = min(
                image_height - full_vertical_start,
                int(round(float(contour_box_height) * scale_factor)) + (safe_padding * 2),
            )
            valid_rectangles.append(
                (full_horizontal_start, full_vertical_start, full_width, full_height)
            )

    valid_rectangles.sort(key=lambda rectangle: rectangle[0], reverse=is_right_to_left)

    if len(valid_rectangles) >= 2:
        selected_pair: list[tuple[int, int, int, int]] = valid_rectangles[:2]
        segmented_pages: list[BookletPageSegment] = []
        page_order_index: int
        for page_order_index in range(len(selected_pair)):
            selected_box: tuple[int, int, int, int] = selected_pair[page_order_index]
            horizontal_position: int = selected_box[0]
            vertical_position: int = selected_box[1]
            box_width: int = selected_box[2]
            box_height: int = selected_box[3]
            cropped_page: np.ndarray = spread_image[
                vertical_position : vertical_position + box_height,
                horizontal_position : horizontal_position + box_width,
            ]
            segment: BookletPageSegment = BookletPageSegment(
                page_image=cropped_page,
                bounding_box=(horizontal_position, vertical_position, box_width, box_height),
                page_index_hint=page_order_index,
            )
            segmented_pages.append(segment)
        return segmented_pages

    horizontal_midpoint: int = image_width // 2
    left_crop: np.ndarray = spread_image[:, :horizontal_midpoint]
    right_crop: np.ndarray = spread_image[:, horizontal_midpoint:]

    if is_right_to_left:
        first_rtl_segment: BookletPageSegment = BookletPageSegment(
            page_image=right_crop,
            bounding_box=(horizontal_midpoint, 0, image_width - horizontal_midpoint, image_height),
            page_index_hint=0,
        )
        second_rtl_segment: BookletPageSegment = BookletPageSegment(
            page_image=left_crop,
            bounding_box=(0, 0, horizontal_midpoint, image_height),
            page_index_hint=1,
        )
        return [first_rtl_segment, second_rtl_segment]

    left_segment: BookletPageSegment = BookletPageSegment(
        page_image=left_crop,
        bounding_box=(0, 0, horizontal_midpoint, image_height),
        page_index_hint=0,
    )
    right_segment: BookletPageSegment = BookletPageSegment(
        page_image=right_crop,
        bounding_box=(horizontal_midpoint, 0, image_width - horizontal_midpoint, image_height),
        page_index_hint=1,
    )
    return [left_segment, right_segment]


def segment_booklet_with_config(
    spread_image: np.ndarray,
    configuration: BookletProcessConfiguration,
) -> list[BookletPageSegment]:
    """
    Segment a booklet spread using a ``BookletProcessConfiguration`` contract.

    Parameters
    ----------
    spread_image : np.ndarray
        Source BGR booklet spread image.
    configuration : BookletProcessConfiguration
        Typed booklet segmentation configuration.

    Returns
    -------
    list[BookletPageSegment]
        Ordered list of isolated booklet page segments.
    """
    segments: list[BookletPageSegment] = segment_booklet_spread(
        spread_image=spread_image,
        split_dual_pages=configuration.split_dual_pages,
        margin_padding_pixels=configuration.margin_padding_pixels,
        reading_direction=configuration.reading_direction,
        spread_orientation=configuration.spread_orientation,
        spread_aspect_ratio_threshold=configuration.spread_aspect_ratio_threshold,
    )
    return segments
