"""
Unified scanner discovery, transport negotiation, and multi-protocol scan manager.
"""

from __future__ import annotations

# eSCL = Enhanced Scanner Client Language
# WIA = Windows Image Acquisition
# COM = Component Object Model
# USB = Universal Serial Bus
# DPI = Dots Per Inch
# PNG = Portable Network Graphics
# JPEG = Joint Photographic Experts Group
# TCP = Transmission Control Protocol

import datetime
from pathlib import Path
from typing import Optional

from white_pepper.algorithms.geometry import ResolvedScanRegion
from white_pepper.config import ScanConfiguration
from white_pepper.hardware.escl_client import (
    DEFAULT_ESCL_IP,
    DEFAULT_ESCL_PORT,
    EsclClient,
)
from white_pepper.hardware.powershell_bridge import execute_powershell_wia_scan
from white_pepper.hardware.wia_client import WiaClient


class ScannerManager:
    """
    Multi-transport hardware acquisition orchestrator supporting eSCL, WIA COM, and PowerShell WIA.

    Attributes
    ----------
    destination_directory : Path
        Default destination directory for auto-generated scan files.
    escl_client : EsclClient
        Configured wireless eSCL REST client.
    wia_client : WiaClient
        Configured local Windows WIA COM client.
    """

    destination_directory: Path
    escl_client: EsclClient
    wia_client: WiaClient

    def __init__(
        self,
        destination_directory: Path = Path(r"D:\Pictures\Scanned"),
        escl_host: str = DEFAULT_ESCL_IP,
        escl_port: int = DEFAULT_ESCL_PORT,
    ) -> None:
        """
        Initialize the unified scanner manager.

        Parameters
        ----------
        destination_directory : Path, optional
            Default output directory for saved scans, by default ``Path(r"D:\\Pictures\\Scanned")``.
        escl_host : str, optional
            IPv4 address or hostname of the wireless eSCL scanner, by default ``DEFAULT_ESCL_IP``.
        escl_port : int, optional
            TCP port of the wireless eSCL scanner, by default ``DEFAULT_ESCL_PORT``.

        Returns
        -------
        None
        """
        self.destination_directory = destination_directory
        self.destination_directory.mkdir(parents=True, exist_ok=True)
        self.escl_client = EsclClient(host_address=escl_host, port_number=escl_port)
        self.wia_client = WiaClient()

    def generate_filepath(
        self,
        prefix: str = "scan",
        maximum_quality: bool = False,
        half_area: bool = False,
        extension: str = "png",
        resolution_dpi: Optional[int] = None,
        paper_size: Optional[str] = None,
        target_directory: Optional[Path] = None,
    ) -> Path:
        """
        Construct a collision-safe timestamped output filepath with descriptive metadata tags.

        Parameters
        ----------
        prefix : str, optional
            Filename prefix, by default ``"scan"``.
        maximum_quality : bool, optional
            Legacy flag indicating 1200 DPI maximum quality, by default ``False``.
        half_area : bool, optional
            Legacy flag indicating half-platen receipt capture, by default ``False``.
        extension : str, optional
            File extension without a leading dot, by default ``"png"``.
        resolution_dpi : Optional[int], optional
            Explicit optical DPI embedded into the filename tag when provided, by default ``None``.
        paper_size : Optional[str], optional
            Explicit paper size key embedded when non-full, by default ``None``.
        target_directory : Optional[Path], optional
            Directory override replacing ``self.destination_directory``, by default ``None``.

        Returns
        -------
        Path
            Generated output file path.
        """
        now_instant: datetime.datetime = datetime.datetime.now()
        timestamp_string: str = now_instant.strftime("%Y%m%d_%H%M%S")
        cleaned_extension: str = extension.strip().lower().lstrip(".")
        if cleaned_extension == "jpeg":
            cleaned_extension = "jpg"

        quality_tag: str
        if resolution_dpi is not None:
            quality_tag = f"{resolution_dpi}dpi"
        else:
            quality_tag = "max" if maximum_quality else "std"

        area_tag: str = ""
        if paper_size is not None and paper_size.strip().lower() not in ("", "full"):
            sanitized_paper: str = paper_size.strip().lower().replace(" ", "-")
            area_tag = f"_{sanitized_paper}"
        elif half_area:
            area_tag = "_half"

        sanitized_prefix: str = prefix.strip() or "scan"
        base_directory: Path = (
            target_directory if target_directory is not None else self.destination_directory
        )
        base_directory.mkdir(parents=True, exist_ok=True)

        filename: str = f"{sanitized_prefix}_{timestamp_string}_{quality_tag}{area_tag}.{cleaned_extension}"
        candidate_path: Path = base_directory / filename
        collision_counter: int = 1
        while candidate_path.exists():
            deduplicated_name: str = (
                f"{sanitized_prefix}_{timestamp_string}_{collision_counter:02d}_"
                f"{quality_tag}{area_tag}.{cleaned_extension}"
            )
            candidate_path = base_directory / deduplicated_name
            collision_counter += 1

        return candidate_path

    def acquire_with_config(
        self,
        configuration: ScanConfiguration,
        output_file_path: Optional[Path] = None,
    ) -> Path:
        """
        Execute a hardware scan governed by a strongly-typed ``ScanConfiguration`` contract.

        Parameters
        ----------
        configuration : ScanConfiguration
            Complete scan geometry, optical, adjustment, and transport configuration.
        output_file_path : Optional[Path], optional
            Explicit filepath override replacing auto-generated naming, by default ``None``.

        Returns
        -------
        Path
            Path to the saved scan file on disk.

        Raises
        ------
        ConnectionError
            If ``backend_mode == "escl"`` and the wireless scanner is unreachable.
        RuntimeError
            If all permitted transport backends fail to complete the scan.
        """
        if (
            configuration.escl_host != self.escl_client.host_address
            or configuration.escl_port != self.escl_client.port_number
        ):
            self.escl_client = EsclClient(
                host_address=configuration.escl_host,
                port_number=configuration.escl_port,
            )

        resolved_region: ResolvedScanRegion = configuration.resolve_region()
        if resolved_region.was_clamped:
            print(f"  [Platen Clamping Notice] {resolved_region.clamping_notice}")

        effective_dpi: int = configuration.effective_dpi()
        normalized_format: str = configuration.normalized_extension()
        resolved_folder: Path = configuration.target_directory()
        resolved_folder.mkdir(parents=True, exist_ok=True)

        target_path: Path
        if output_file_path is not None:
            target_path = output_file_path
        elif configuration.output_file_path is not None:
            target_path = configuration.output_file_path
        else:
            target_path = self.generate_filepath(
                prefix=configuration.filename_prefix,
                maximum_quality=configuration.maximum_quality,
                half_area=(resolved_region.paper_size_key == "receipt-half"),
                extension=normalized_format,
                resolution_dpi=effective_dpi,
                paper_size=resolved_region.paper_size_key,
                target_directory=resolved_folder,
            )

        backend_choice: str = configuration.backend_mode.strip().lower()
        allow_escl: bool = backend_choice in ("auto", "escl") and (
            configuration.prefer_escl or backend_choice == "escl"
        )
        allow_wia_com: bool = backend_choice in ("auto", "wia")
        allow_powershell: bool = backend_choice in ("auto", "wia", "powershell")

        if allow_escl:
            if self.escl_client.is_reachable():
                try:
                    print(
                        f"  [Transport: eSCL] Acquiring wirelessly from "
                        f"{self.escl_client.host_address}:{self.escl_client.port_number} "
                        f"({effective_dpi} DPI, {resolved_region.paper_size_key}, {configuration.color_mode})..."
                    )
                    saved_escl_path: Path = self.escl_client.scan(
                        output_file_path=target_path,
                        resolution_dpi=effective_dpi,
                        intent_type=configuration.escl_intent_name(),
                        color_mode=configuration.color_mode,
                        brightness=configuration.brightness,
                        contrast=configuration.contrast,
                        rotation_degrees=configuration.rotation_degrees,
                        auto_crop_whitespace=configuration.auto_crop_whitespace,
                        output_format=normalized_format,
                        jpeg_quality=configuration.jpeg_quality,
                        enable_beep=configuration.enable_beep,
                        resolved_region=resolved_region,
                    )
                    return saved_escl_path
                except Exception as escl_error:
                    if backend_choice == "escl":
                        raise
                    print(
                        f"  [Notice] eSCL acquisition failed ({escl_error}). Falling back to local WIA..."
                    )
            elif backend_choice == "escl":
                raise ConnectionError(
                    f"Wireless eSCL scanner at {self.escl_client.host_address}:"
                    f"{self.escl_client.port_number} is unreachable."
                )

        if allow_wia_com:
            try:
                print("  [Transport: WIA COM] Acquiring via local Windows Image Acquisition...")
                saved_wia_path: Path = self.wia_client.scan(
                    output_file_path=target_path,
                    resolution_dpi=effective_dpi,
                    maximum_quality=configuration.maximum_quality,
                    color_mode=configuration.color_mode,
                    brightness=configuration.brightness,
                    contrast=configuration.contrast,
                    rotation_degrees=configuration.rotation_degrees,
                    auto_crop_whitespace=configuration.auto_crop_whitespace,
                    output_format=normalized_format,
                    jpeg_quality=configuration.jpeg_quality,
                    enable_beep=configuration.enable_beep,
                    resolved_region=resolved_region,
                )
                return saved_wia_path
            except Exception as wia_error:
                if not allow_powershell:
                    raise
                print(
                    f"  [Notice] Direct WIA COM scan failed ({wia_error}). "
                    "Falling back to PowerShell bridge..."
                )

        if allow_powershell:
            print("  [Transport: PowerShell WIA] Acquiring via PowerShell bridge...")
            saved_ps_path: Path = execute_powershell_wia_scan(
                output_file_path=target_path,
                resolution_dpi=effective_dpi,
                maximum_quality=configuration.maximum_quality,
                color_mode=configuration.color_mode,
                brightness=configuration.brightness,
                contrast=configuration.contrast,
                rotation_degrees=configuration.rotation_degrees,
                auto_crop_whitespace=configuration.auto_crop_whitespace,
                output_format=normalized_format,
                jpeg_quality=configuration.jpeg_quality,
                enable_beep=configuration.enable_beep,
                resolved_region=resolved_region,
            )
            return saved_ps_path

        raise RuntimeError(f"Unsupported backend_mode '{configuration.backend_mode}'.")

    def acquire_scan(
        self,
        output_file_path: Optional[Path] = None,
        resolution_dpi: int = 300,
        maximum_quality: bool = False,
        half_area: bool = False,
        scan_width_inches: float = 8.5,
        scan_height_inches: float = 11.69,
        prefer_escl: bool = True,
    ) -> Path:
        """
        Execute a scan using the legacy positional/keyword parameter interface.

        Parameters
        ----------
        output_file_path : Optional[Path], optional
            Destination filepath override, by default ``None``.
        resolution_dpi : int, optional
            Optical resolution in dots per inch, by default ``300``.
        maximum_quality : bool, optional
            Use 1200 DPI hardware maximum when ``True``, by default ``False``.
        half_area : bool, optional
            Restrict scan height to 50 percent when ``True``, by default ``False``.
        scan_width_inches : float, optional
            Capture width in inches, by default ``8.5``.
        scan_height_inches : float, optional
            Capture height in inches, by default ``11.69``.
        prefer_escl : bool, optional
            Attempt wireless eSCL before USB WIA when ``True``, by default ``True``.

        Returns
        -------
        Path
            Path to the saved scan file.
        """
        target_resolution: int = 1200 if maximum_quality else resolution_dpi
        target_path: Path
        if output_file_path is None:
            target_path = self.generate_filepath(
                maximum_quality=maximum_quality,
                half_area=half_area,
            )
        else:
            target_path = output_file_path

        is_custom_box: bool = (
            abs(scan_width_inches - 8.5) > 0.02 or abs(scan_height_inches - 11.69) > 0.02
        )
        legacy_configuration: ScanConfiguration
        if is_custom_box:
            effective_height: float = (
                scan_height_inches / 2.0 if half_area else scan_height_inches
            )
            legacy_configuration = ScanConfiguration(
                destination_directory=self.destination_directory,
                output_file_path=target_path,
                paper_size="custom",
                custom_width=scan_width_inches,
                custom_height=effective_height,
                measurement_unit="in",
                resolution_dpi=target_resolution,
                maximum_quality=maximum_quality,
                prefer_escl=prefer_escl,
                escl_host=self.escl_client.host_address,
                escl_port=self.escl_client.port_number,
            )
        else:
            legacy_configuration = ScanConfiguration(
                destination_directory=self.destination_directory,
                output_file_path=target_path,
                paper_size="receipt-half" if half_area else "full",
                area_mode="half" if half_area else "full",
                resolution_dpi=target_resolution,
                maximum_quality=maximum_quality,
                prefer_escl=prefer_escl,
                escl_host=self.escl_client.host_address,
                escl_port=self.escl_client.port_number,
            )

        saved_path: Path = self.acquire_with_config(
            configuration=legacy_configuration,
            output_file_path=target_path,
        )
        return saved_path
