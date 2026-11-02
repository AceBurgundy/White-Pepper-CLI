"""
PowerShell Windows Image Acquisition (WIA) fallback bridge script generator.

Executes out-of-process PowerShell WIA COM acquisition when in-process Python
``win32com`` dispatch encounters apartment-threading or driver registration barriers.
"""

from __future__ import annotations

# WIA = Windows Image Acquisition
# COM = Component Object Model
# DPI = Dots Per Inch
# PDF = Portable Document Format
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TIFF = Tagged Image File Format
# BMP = Bitmap Image Format

from pathlib import Path
import subprocess
import tempfile
from typing import Optional

import cv2
import numpy as np

from white_pepper.algorithms.geometry import ResolvedScanRegion, resolve_scan_region
from white_pepper.hardware.escl_client import apply_post_scan_adjustments_and_save
from white_pepper.hardware.wia_client import WIA_DATA_TYPE_MAPPING
from white_pepper.utils.audio import play_completion_beep

WIA_FORMAT_PNG_GUID: str = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"


def execute_powershell_wia_scan(
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
    Acquire a scan by invoking an out-of-process PowerShell WIA automation script.

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
        If the PowerShell WIA subprocess exits with a non-zero status or fails to write image data.
    """
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    active_region: ResolvedScanRegion
    if resolved_region is not None:
        active_region = resolved_region
    elif half_area:
        active_region = resolve_scan_region(paper_size="receipt-half")
    else:
        active_region = resolve_scan_region(paper_size="full")

    effective_dpi: int = 1200 if maximum_quality else resolution_dpi
    pixel_bounds: tuple[int, int, int, int] = active_region.pixel_bounds(effective_dpi)
    horizontal_start_pixels: int = pixel_bounds[0]
    vertical_start_pixels: int = pixel_bounds[1]
    width_pixels: int = pixel_bounds[2]
    height_pixels: int = pixel_bounds[3]

    wia_data_type: int = WIA_DATA_TYPE_MAPPING.get(color_mode.strip().lower(), 3)
    clamped_brightness: int = max(-100, min(100, brightness))
    clamped_contrast: int = max(-100, min(100, contrast))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temporary_file:
        temporary_png_path: Path = Path(temporary_file.name)
    if temporary_png_path.exists():
        temporary_png_path.unlink()

    escaped_transfer_path: str = str(temporary_png_path).replace("'", "''")
    use_max_string: str = "$true" if maximum_quality else "$false"
    is_full_platen_string: str = "$true" if active_region.is_full_platen else "$false"

    powershell_script: str = f"""
$ErrorActionPreference = 'Stop'
$useMaxQuality = {use_max_string}
$isFullPlaten = {is_full_platen_string}
$targetStandardDpi = {effective_dpi}
$wiaDataType = {wia_data_type}
$startXPx = {horizontal_start_pixels}
$startYPx = {vertical_start_pixels}
$widthPx = {width_pixels}
$heightPx = {height_pixels}
$relBrightness = {clamped_brightness}
$relContrast = {clamped_contrast}

$deviceManager = New-Object -ComObject WIA.DeviceManager
$scannerDevice = $null

foreach ($deviceInfo in $deviceManager.DeviceInfos) {{
    if ($deviceInfo.Type -eq 1 -or $deviceInfo.Type -eq 65535 -or $deviceInfo.Properties.Item('Name').Value -match 'scan|tank|print') {{
        $scannerDevice = $deviceInfo.Connect()
        break
    }}
}}

if ($null -eq $scannerDevice) {{
    Write-Error "No WIA scanner device found connected."
    exit 1
}}

$scannerItem = $scannerDevice.Items.Item(1)

function Set-ResolutionProperty($item, $propertyName, $maxQuality, $standardDpi) {{
    $chosenDpi = [int32]$standardDpi
    try {{
        $prop = $item.Properties.Item($propertyName)
        if ($prop.SubType -eq 1) {{
            if ($maxQuality) {{
                $chosenDpi = [int32]$prop.SubTypeMax
            }} else {{
                $chosenDpi = [int32]([Math]::Min([Math]::Max($prop.SubTypeMin, $standardDpi), $prop.SubTypeMax))
            }}
        }} elseif ($prop.SubType -eq 2) {{
            $vals = [int[]]$prop.SubTypeValues
            if ($maxQuality) {{
                $chosenDpi = [int32](($vals | Measure-Object -Maximum).Maximum)
            }} elseif ($vals -contains $standardDpi) {{
                $chosenDpi = [int32]$standardDpi
            }} else {{
                $chosenDpi = [int32](($vals | Sort-Object {{ [Math]::Abs($_ - $standardDpi) }})[0])
            }}
        }}
        $prop.Value = [int32]$chosenDpi
    }} catch {{}}
    return [int32]$chosenDpi
}}

function Set-BoundedProperty($item, $propertyName, [int32]$desiredVal, [bool]$useMax = $false) {{
    try {{
        $prop = $item.Properties.Item($propertyName)
        if ($prop.SubType -eq 1) {{
            $maxVal = [int32]$prop.SubTypeMax
            $minVal = [int32]$prop.SubTypeMin
            if ($useMax) {{
                $prop.Value = $maxVal
            }} else {{
                $prop.Value = [int32]([Math]::Min([Math]::Max($minVal, $desiredVal), $maxVal))
            }}
        }} else {{
            $prop.Value = $desiredVal
        }}
    }} catch {{}}
}}

function Set-RelativeTone($item, $propertyName, [int32]$percent) {{
    if ($percent -eq 0) {{ return }}
    try {{
        $prop = $item.Properties.Item($propertyName)
        if ($prop.SubType -eq 1) {{
            $minVal = [double]$prop.SubTypeMin
            $maxVal = [double]$prop.SubTypeMax
            $mid = ($minVal + $maxVal) / 2.0
            $span = ($maxVal - $minVal) / 2.0
            $mapped = [int32][Math]::Round($mid + (($percent / 100.0) * $span))
            $prop.Value = [int32]([Math]::Min([Math]::Max($minVal, $mapped), $maxVal))
        }}
    }} catch {{}}
}}

try {{ $scannerItem.Properties.Item("Data Type").Value = [int32]$wiaDataType }} catch {{}}

$actualDpi = Set-ResolutionProperty $scannerItem "Horizontal Resolution" $useMaxQuality $targetStandardDpi
[void](Set-ResolutionProperty $scannerItem "Vertical Resolution" $useMaxQuality $actualDpi)

if ($actualDpi -ne $targetStandardDpi -and $targetStandardDpi -gt 0) {{
    $scaleRatio = [double]$actualDpi / [double]$targetStandardDpi
    $startXPx = [int32][Math]::Round($startXPx * $scaleRatio)
    $startYPx = [int32][Math]::Round($startYPx * $scaleRatio)
    $widthPx = [int32][Math]::Max(1, [Math]::Round($widthPx * $scaleRatio))
    $heightPx = [int32][Math]::Max(1, [Math]::Round($heightPx * $scaleRatio))
}}

Set-BoundedProperty $scannerItem "Horizontal Start Position" $startXPx $false
Set-BoundedProperty $scannerItem "Vertical Start Position" $startYPx $false

if ($isFullPlaten) {{
    Set-BoundedProperty $scannerItem "Horizontal Extent" 0 $true
    Set-BoundedProperty $scannerItem "Vertical Extent" 0 $true
}} else {{
    Set-BoundedProperty $scannerItem "Horizontal Extent" $widthPx $false
    Set-BoundedProperty $scannerItem "Vertical Extent" $heightPx $false
}}

Set-RelativeTone $scannerItem "Brightness" $relBrightness
Set-RelativeTone $scannerItem "Contrast" $relContrast

$image = $scannerItem.Transfer("{WIA_FORMAT_PNG_GUID}")
$image.SaveFile('{escaped_transfer_path}')
Write-Output "ACTUAL_DPI:$actualDpi"
"""

    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", powershell_script],
            capture_output=True,
            text=True,
            check=False,
        )

        if completed_process.returncode != 0:
            error_details: str = completed_process.stderr.strip() or completed_process.stdout.strip()
            raise RuntimeError(f"PowerShell WIA bridge scan failed: {error_details}")

        negotiated_dpi: int = effective_dpi
        output_line: str
        for output_line in completed_process.stdout.splitlines():
            if output_line.strip().startswith("ACTUAL_DPI:"):
                try:
                    negotiated_dpi = int(output_line.strip().split(":", 1)[1])
                except ValueError:
                    negotiated_dpi = effective_dpi

        decoded_bgr: Optional[np.ndarray] = cv2.imread(str(temporary_png_path), cv2.IMREAD_COLOR)
        if decoded_bgr is None:
            raise RuntimeError("Failed to read temporary PNG from PowerShell WIA bridge.")
        apply_post_scan_adjustments_and_save(
            source_bgr_image=decoded_bgr,
            output_file_path=output_file_path,
            resolution_dpi=negotiated_dpi,
            color_mode=color_mode,
            brightness=clamped_brightness,
            contrast=clamped_contrast,
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
