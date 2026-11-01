"""
Windows Image Acquisition (WIA) Component Object Model (COM) scanner client.

Provides direct USB/local WIA scanner enumeration, property negotiation for
resolution, platen extents, color mode, and brightness/contrast, plus post-scan
multi-format conversion.
"""

from __future__ import annotations

# WIA = Windows Image Acquisition
# COM = Component Object Model
# USB = Universal Serial Bus
# DPI = Dots Per Inch
# PDF = Portable Document Format
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format

from pathlib import Path
import tempfile
from typing import Optional

import cv2
import numpy as np

from white_pepper.algorithms.geometry import ResolvedScanRegion, resolve_scan_region
from white_pepper.hardware.escl_client import apply_post_scan_adjustments_and_save
from white_pepper.utils.audio import play_completion_beep

WIA_FORMAT_PNG_GUID: str = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"
WIA_DEVICE_TYPE_SCANNER: int = 1
WIA_PROPERTY_SUBTYPE_NONE: int = 0
WIA_PROPERTY_SUBTYPE_RANGE: int = 1
WIA_PROPERTY_SUBTYPE_LIST: int = 2

WIA_DATA_TYPE_MAPPING: dict[str, int] = {
    "bw": 0,
    "grayscale": 2,
    "color": 3,
}


class WiaClient:
    """
    Local Windows Image Acquisition (WIA 2.0) COM automation client.
    """

    def __init__(self) -> None:
        """
        Initialize the WIA COM client wrapper.

        Returns
        -------
        None
        """

    def _get_property_by_name_or_id(
        self,
        properties_collection: object,
        property_name: str,
        property_id: Optional[int] = None,
    ) -> Optional[object]:
        """
        Retrieve a WIA COM property object by display name or numeric WIA PropertyID.

        Parameters
        ----------
        properties_collection : object
            WIA ``Properties`` COM collection on a device or scanner item.
        property_name : str
            Canonical WIA property name (e.g., ``"Horizontal Resolution"``).
        property_id : Optional[int], optional
            Fallback numeric WIA PropertyID (e.g., ``6147``), by default ``None``.

        Returns
        -------
        Optional[object]
            Matching WIA COM ``Property`` object, or ``None`` if unavailable.
        """
        try:
            callable_collection: object = properties_collection
            direct_property: object = callable_collection(property_name)  # type: ignore[operator]
            return direct_property
        except Exception:
            pass

        if property_id is not None:
            try:
                property_item: object
                for property_item in properties_collection:  # type: ignore[attr-defined]
                    current_id: int = int(getattr(property_item, "PropertyID", -1))
                    if current_id == property_id:
                        return property_item
            except Exception:
                pass
        return None

    def _configure_property_value(
        self,
        property_item: Optional[object],
        target_value: int,
        maximize_if_range: bool = False,
        fraction: float = 1.0,
    ) -> Optional[int]:
        """
        Assign a bounded integer value to a WIA COM property respecting SubType constraints.

        Parameters
        ----------
        property_item : Optional[object]
            WIA COM ``Property`` instance to mutate, or ``None``.
        target_value : int
            Desired integer value when ``maximize_if_range`` is ``False``.
        maximize_if_range : bool, optional
            Select maximum supported range/list value scaled by ``fraction``, by default ``False``.
        fraction : float, optional
            Multiplicative ratio applied when ``maximize_if_range`` is active, by default ``1.0``.

        Returns
        -------
        Optional[int]
            Assigned integer value, or ``None`` if assignment was unsupported.
        """
        if property_item is None:
            return None

        try:
            subtype: int = int(getattr(property_item, "SubType", WIA_PROPERTY_SUBTYPE_NONE))
            if subtype == WIA_PROPERTY_SUBTYPE_RANGE:
                max_value: int = int(getattr(property_item, "SubTypeMax"))
                min_value: int = int(getattr(property_item, "SubTypeMin"))
                chosen_range_value: int
                if maximize_if_range or fraction < 1.0:
                    chosen_range_value = max(min_value, int(round(float(max_value) * fraction)))
                else:
                    chosen_range_value = max(min_value, min(max_value, target_value))
                setattr(property_item, "Value", chosen_range_value)
                return chosen_range_value
            if subtype == WIA_PROPERTY_SUBTYPE_LIST:
                raw_values: object = getattr(property_item, "SubTypeValues")
                available_values: list[int] = [int(candidate) for candidate in raw_values]  # type: ignore[attr-defined]
                if available_values:
                    chosen_list_value: int
                    if maximize_if_range:
                        chosen_list_value = max(available_values)
                    else:
                        chosen_list_value = min(
                            available_values,
                            key=lambda candidate_dpi: abs(candidate_dpi - target_value),
                        )
                    setattr(property_item, "Value", chosen_list_value)
                    return chosen_list_value
            else:
                setattr(property_item, "Value", target_value)
                return target_value
        except Exception:
            return None
        return None

    def _configure_relative_tone_property(
        self,
        property_item: Optional[object],
        relative_percent: int,
    ) -> None:
        """
        Map a normalized ``[-100, 100]`` tone adjustment onto a WIA range property.

        Parameters
        ----------
        property_item : Optional[object]
            WIA ``Brightness`` (6154) or ``Contrast`` (6155) COM property object.
        relative_percent : int
            Normalized adjustment percentage in ``[-100, 100]``.

        Returns
        -------
        None
        """
        if property_item is None or relative_percent == 0:
            return

        try:
            subtype: int = int(getattr(property_item, "SubType", WIA_PROPERTY_SUBTYPE_NONE))
            clamped_percent: int = max(-100, min(100, relative_percent))
            if subtype == WIA_PROPERTY_SUBTYPE_RANGE:
                min_value: int = int(getattr(property_item, "SubTypeMin"))
                max_value: int = int(getattr(property_item, "SubTypeMax"))
                midpoint: float = float(min_value + max_value) / 2.0
                half_span: float = float(max_value - min_value) / 2.0
                mapped_value: int = int(
                    round(midpoint + (float(clamped_percent) / 100.0) * half_span)
                )
                bounded_value: int = max(min_value, min(max_value, mapped_value))
                setattr(property_item, "Value", bounded_value)
            else:
                setattr(property_item, "Value", clamped_percent)
        except Exception:
            pass

    def scan(
        self,
        output_file_path: Path,
        resolution_dpi: int = 300,
        maximum_quality: bool = False,
        half_area: bool = False,
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
        Acquire a scan over local Windows WIA COM with full region and format support.

        Parameters
        ----------
        output_file_path : Path
            Target filesystem path for the saved scan.
        resolution_dpi : int, optional
            Desired optical resolution in dots per inch, by default ``300``.
        maximum_quality : bool, optional
            Select maximum hardware DPI when ``True``, by default ``False``.
        half_area : bool, optional
            Legacy flag scanning top 50 percent of platen height, by default ``False``.
        color_mode : str, optional
            Color representation (``"color"``, ``"grayscale"``, or ``"bw"``), by default ``"color"``.
        brightness : int, optional
            Relative brightness adjustment in ``[-100, 100]``, by default ``0``.
        contrast : int, optional
            Relative contrast adjustment in ``[-100, 100]``, by default ``0``.
        rotation_degrees : int, optional
            Clockwise post-scan rotation angle in ``{0, 90, 180, 270}``, by default ``0``.
        auto_crop_whitespace : bool, optional
            Trim uniform white borders when ``True``, by default ``False``.
        output_format : str, optional
            Output file format (``"png"``, ``"jpg"``, ``"tiff"``, ``"bmp"``, ``"pdf"``),
            by default ``"png"``.
        jpeg_quality : int, optional
            JPEG encoding quality in ``[1, 100]``, by default ``95``.
        enable_beep : bool, optional
            Play acoustic completion notification when ``True``, by default ``True``.
        resolved_region : Optional[ResolvedScanRegion], optional
            Resolved physical platen bounding box, by default ``None``.

        Returns
        -------
        Path
            Path to the written scan file.

        Raises
        ------
        RuntimeError
            If ``WIA.DeviceManager`` cannot be instantiated or no local WIA scanner is connected.
        """
        try:
            import win32com.client  # type: ignore

            device_manager: object = win32com.client.Dispatch("WIA.DeviceManager")
        except Exception as dispatch_error:
            raise RuntimeError(
                f"Failed to instantiate WIA.DeviceManager COM server: {dispatch_error}"
            ) from dispatch_error

        scanner_device_info: Optional[object] = None
        device_info_collection: object = getattr(device_manager, "DeviceInfos")
        device_info: object
        for device_info in device_info_collection:  # type: ignore[attr-defined]
            device_type: int = int(getattr(device_info, "Type", 0))
            if device_type == WIA_DEVICE_TYPE_SCANNER:
                scanner_device_info = device_info
                break

        if scanner_device_info is None:
            raise RuntimeError("No local USB WIA scanner device found connected.")

        scanner_device: object = scanner_device_info.Connect()  # type: ignore[attr-defined]
        scanner_items: object = getattr(scanner_device, "Items")
        scanner_item: object = scanner_items[1]  # type: ignore[index]
        properties_collection: object = getattr(scanner_item, "Properties")

        active_region: ResolvedScanRegion
        if resolved_region is not None:
            active_region = resolved_region
        elif half_area:
            active_region = resolve_scan_region(paper_size="receipt-half")
        else:
            active_region = resolve_scan_region(paper_size="full")

        wia_data_type: int = WIA_DATA_TYPE_MAPPING.get(color_mode.strip().lower(), 3)
        data_type_property: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Data Type",
            6146,
        )
        if data_type_property is not None:
            try:
                setattr(data_type_property, "Value", wia_data_type)
            except Exception:
                pass

        horiz_res_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Horizontal Resolution",
            6147,
        )
        negotiated_dpi: Optional[int] = self._configure_property_value(
            horiz_res_prop,
            resolution_dpi,
            maximize_if_range=maximum_quality,
        )
        effective_dpi: int = negotiated_dpi if negotiated_dpi is not None else resolution_dpi

        vert_res_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Vertical Resolution",
            6148,
        )
        self._configure_property_value(
            vert_res_prop,
            effective_dpi,
            maximize_if_range=maximum_quality,
        )

        pixel_bounds: tuple[int, int, int, int] = active_region.pixel_bounds(effective_dpi)
        horizontal_start_pixels: int = pixel_bounds[0]
        vertical_start_pixels: int = pixel_bounds[1]
        width_pixels: int = pixel_bounds[2]
        height_pixels: int = pixel_bounds[3]

        horiz_start_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Horizontal Start Position",
            6149,
        )
        self._configure_property_value(horiz_start_prop, horizontal_start_pixels)

        vert_start_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Vertical Start Position",
            6150,
        )
        self._configure_property_value(vert_start_prop, vertical_start_pixels)

        horiz_extent_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Horizontal Extent",
            6151,
        )
        if active_region.is_full_platen:
            self._configure_property_value(horiz_extent_prop, 0, maximize_if_range=True, fraction=1.0)
        else:
            self._configure_property_value(horiz_extent_prop, width_pixels)

        vert_extent_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Vertical Extent",
            6152,
        )
        if active_region.is_full_platen:
            self._configure_property_value(vert_extent_prop, 0, maximize_if_range=True, fraction=1.0)
        else:
            self._configure_property_value(vert_extent_prop, height_pixels)

        brightness_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Brightness",
            6154,
        )
        self._configure_relative_tone_property(brightness_prop, brightness)

        contrast_prop: Optional[object] = self._get_property_by_name_or_id(
            properties_collection,
            "Contrast",
            6155,
        )
        self._configure_relative_tone_property(contrast_prop, contrast)

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        requires_post_processing: bool = (
            rotation_degrees != 0
            or auto_crop_whitespace
            or output_format.strip().lower().lstrip(".") not in ("png",)
            or output_file_path.suffix.strip().lower() not in ("", ".png")
        )

        if not requires_post_processing:
            image_result: object = scanner_item.Transfer(WIA_FORMAT_PNG_GUID)  # type: ignore[attr-defined]
            image_result.SaveFile(str(output_file_path))  # type: ignore[attr-defined]
        else:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temporary_file:
                temporary_png_path: Path = Path(temporary_file.name)
            try:
                if temporary_png_path.exists():
                    temporary_png_path.unlink()
                raw_transfer: object = scanner_item.Transfer(WIA_FORMAT_PNG_GUID)  # type: ignore[attr-defined]
                raw_transfer.SaveFile(str(temporary_png_path))  # type: ignore[attr-defined]
                decoded_wia_bgr: Optional[np.ndarray] = cv2.imread(str(temporary_png_path), cv2.IMREAD_COLOR)
                if decoded_wia_bgr is None:
                    raise RuntimeError("Failed to read temporary PNG transferred from WIA scanner.")
                apply_post_scan_adjustments_and_save(
                    source_bgr_image=decoded_wia_bgr,
                    output_file_path=output_file_path,
                    resolution_dpi=effective_dpi,
                    color_mode=color_mode,
                    brightness=brightness,
                    contrast=contrast,
                    rotation_degrees=rotation_degrees,
                    auto_crop_whitespace=auto_crop_whitespace,
                    output_format=output_format,
                    jpeg_quality=jpeg_quality,
                    apply_software_tone=False,
                )
            finally:
                if temporary_png_path.exists():
                    temporary_png_path.unlink()

        if enable_beep:
            play_completion_beep()

        return output_file_path
