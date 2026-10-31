"""
Optical Character Recognition orientation detection and automatic rotation correction.
"""

from __future__ import annotations

# OCR = Optical Character Recognition
# ONNX = Open Neural Network Exchange
# BGR = Blue Green Red

from typing import Optional

import cv2
import numpy as np

# RapidOCR = Fast cross-platform ONNX-based text recognition engine
RAPID_OCR_AVAILABLE: bool = False
try:
    from rapidocr_onnxruntime import RapidOCR

    RAPID_OCR_AVAILABLE = True
except ImportError:
    RapidOCR: Optional[object] = None  # type: ignore[no-redef]


def detect_upright_orientation_angle(
    image: np.ndarray,
    ocr_engine: Optional[object] = None,
) -> int:
    """
    Determine the rotation angle required to orient text upright.

    Parameters
    ----------
    image : np.ndarray
        Input image in BGR format.
    ocr_engine : object, optional
        Pre-instantiated RapidOCR instance (constructed if None).

    Returns
    -------
    int
        Correction angle in degrees clockwise (0, 90, 180, or 270).
    """
    if not RAPID_OCR_AVAILABLE or image is None or image.size == 0:
        return 0

    engine: object
    if ocr_engine is None:
        try:
            engine = RapidOCR()  # type: ignore[misc]
        except Exception:
            return 0
    else:
        engine = ocr_engine

    # Downscale for fast text detection
    target_max_dimension: int = 1200
    current_max_dimension: int = max(image.shape[0], image.shape[1])
    scale: float = 1.0
    working_image: np.ndarray

    if current_max_dimension > target_max_dimension:
        scale = float(target_max_dimension) / float(current_max_dimension)
        resized_width: int = int(round(float(image.shape[1]) * scale))
        resized_height: int = int(round(float(image.shape[0]) * scale))
        working_image = cv2.resize(image, (resized_width, resized_height))
    else:
        working_image = image

    # Test four cardinal orientations and compute aggregate OCR confidence
    rotations_to_test: list[tuple[int, Optional[int]]] = [
        (0, None),
        (90, cv2.ROTATE_90_CLOCKWISE),
        (180, cv2.ROTATE_180),
        (270, cv2.ROTATE_90_COUNTERCLOCKWISE),
    ]

    best_angle: int = 0
    best_score: float = -1.0

    for angle_degrees, cv_rotation_code in rotations_to_test:
        test_frame: np.ndarray
        if cv_rotation_code is None:
            test_frame = working_image
        else:
            test_frame = cv2.rotate(working_image, cv_rotation_code)

        try:
            # engine returns: (results, elapse_list)
            ocr_call_output: tuple[Optional[list[list[object]]], object] = engine(test_frame)  # type: ignore[operator]
            ocr_results: Optional[list[list[object]]] = ocr_call_output[0]
            if not ocr_results:
                continue

            # Compute sum of confidence scores for high-confidence words
            total_confidence: float = sum(
                float(str(entry_row[2]))
                for entry_row in ocr_results
                if len(entry_row) >= 3 and float(str(entry_row[2])) > 0.5
            )

            if total_confidence > best_score:
                best_score = total_confidence
                best_angle = angle_degrees
        except Exception:
            continue

    return best_angle


def rotate_image_to_upright(
    image: np.ndarray,
    correction_angle_degrees: int,
) -> np.ndarray:
    """
    Apply a cardinal rotation (0, 90, 180, 270 degrees) to orient an image upright.

    Parameters
    ----------
    image : np.ndarray
        Source image array.
    correction_angle_degrees : int
        Rotation angle in degrees (0, 90, 180, or 270).

    Returns
    -------
    np.ndarray
        The rotated upright image.
    """
    if correction_angle_degrees == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if correction_angle_degrees == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if correction_angle_degrees == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image
