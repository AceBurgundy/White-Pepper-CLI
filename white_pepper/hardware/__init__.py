"""
Hardware scanner abstractions, network eSCL clients, and WIA automation drivers.
"""

from __future__ import annotations

# eSCL = Enhanced Scanner Client Language
# WIA = Windows Image Acquisition

from white_pepper.hardware.escl_client import (
    DEFAULT_ESCL_IP,
    DEFAULT_ESCL_PORT,
    EsclClient,
    apply_post_scan_adjustments_and_save,
    crop_whitespace_borders,
    decode_and_clip_escl_payload,
)
from white_pepper.hardware.powershell_bridge import execute_powershell_wia_scan
from white_pepper.hardware.scanner_manager import ScannerManager
from white_pepper.hardware.wia_client import WiaClient

__all__: list[str] = [
    "DEFAULT_ESCL_IP",
    "DEFAULT_ESCL_PORT",
    "EsclClient",
    "WiaClient",
    "execute_powershell_wia_scan",
    "ScannerManager",
    "apply_post_scan_adjustments_and_save",
    "crop_whitespace_borders",
    "decode_and_clip_escl_payload",
]
