"""
Centralized Hardware Diagnostics & Device Inspection CLI.

Inspects local USB WIA imaging devices, probes wireless eSCL network scanners,
verifies discrete resolutions and platen capabilities, exports raw eSCL XML
capabilities, and emits structured JSON reports.
"""

from __future__ import annotations

# CLI = Command Line Interface
# eSCL = Enhanced Scanner Client Language
# WIA = Windows Image Acquisition
# COM = Component Object Model
# USB = Universal Serial Bus
# DPI = Dots Per Inch
# HTTP = Hypertext Transfer Protocol
# TCP = Transmission Control Protocol
# IP = Internet Protocol
# UUID = Universally Unique Identifier
# XML = Extensible Markup Language
# JSON = JavaScript Object Notation

import argparse
import json
from pathlib import Path
import re
from typing import Optional, TypedDict

from white_pepper.hardware.escl_client import DEFAULT_ESCL_IP, DEFAULT_ESCL_PORT, EsclClient


class EsclDiagnosticSummary(TypedDict):
    """Structured diagnostic report for a wireless eSCL scanner endpoint."""

    host: str
    port: int
    endpoint_url: str
    reachable: bool
    make_and_model: str
    uuid: str
    max_width_escl_units: int
    max_height_escl_units: int
    supported_dpi: list[int]
    color_modes: list[str]
    document_formats: list[str]
    saved_capabilities_path: str
    error: str


class WiaDeviceSummary(TypedDict):
    """Structured diagnostic descriptor for a local Windows WIA device."""

    index: int
    name: str
    device_id: str
    device_type: int
    type_label: str


class FullDiagnosticsReport(TypedDict):
    """Combined eSCL and WIA diagnostic report structure."""

    escl: EsclDiagnosticSummary
    wia_devices: list[WiaDeviceSummary]
    wia_error: str


def probe_escl_scanner(
    host: str,
    port: int,
    timeout_seconds: float = 3.0,
    save_capabilities_path: Optional[Path] = None,
    quiet: bool = False,
) -> EsclDiagnosticSummary:
    """
    Probe the wireless eSCL network scanner, parse capabilities, and optionally export XML.

    Parameters
    ----------
    host : str
        IPv4 address or hostname of the eSCL scanner.
    port : int
        HTTP TCP port of the scanner.
    timeout_seconds : float, optional
        Socket and HTTP read timeout in seconds, by default ``3.0``.
    save_capabilities_path : Optional[Path], optional
        Destination path to write raw ``ScannerCapabilities`` XML, by default ``None``.
    quiet : bool, optional
        Suppress human-readable console output when ``True`` (e.g. for ``--json``),
        by default ``False``.

    Returns
    -------
    EsclDiagnosticSummary
        Structured dictionary summarizing eSCL reachability and hardware capabilities.
    """
    client: EsclClient = EsclClient(host_address=host, port_number=port)
    summary: EsclDiagnosticSummary = {
        "host": host,
        "port": port,
        "endpoint_url": client.base_url,
        "reachable": False,
        "make_and_model": "",
        "uuid": "",
        "max_width_escl_units": 0,
        "max_height_escl_units": 0,
        "supported_dpi": [],
        "color_modes": [],
        "document_formats": [],
        "saved_capabilities_path": "",
        "error": "",
    }

    if not quiet:
        print(f"1. Probing Wireless eSCL Endpoint ({host}:{port})")

    if not client.is_reachable(probe_timeout_seconds=timeout_seconds):
        if not quiet:
            print(f"  [Status] Offline / Unreachable at {client.base_url}/ScannerStatus")
        return summary

    summary["reachable"] = True
    if not quiet:
        print("  [Status] Online and responsive (HTTP 200)")

    try:
        capabilities_xml: str = client.query_capabilities(timeout_seconds=timeout_seconds)

        if save_capabilities_path is not None:
            save_capabilities_path.parent.mkdir(parents=True, exist_ok=True)
            save_capabilities_path.write_text(capabilities_xml, encoding="utf-8")
            summary["saved_capabilities_path"] = str(save_capabilities_path)
            if not quiet:
                print(f"  [Saved XML] Capabilities written to {save_capabilities_path}")

        model_match: Optional[re.Match[str]] = re.search(
            r"<pwg:MakeAndModel>(.*?)</pwg:MakeAndModel>",
            capabilities_xml,
        )
        if model_match is not None:
            summary["make_and_model"] = model_match.group(1)

        uuid_match: Optional[re.Match[str]] = re.search(
            r"<scan:UUID>(.*?)</scan:UUID>",
            capabilities_xml,
        )
        if uuid_match is not None:
            summary["uuid"] = uuid_match.group(1)

        max_width_match: Optional[re.Match[str]] = re.search(
            r"<scan:MaxWidth>(\d+)</scan:MaxWidth>",
            capabilities_xml,
        )
        max_height_match: Optional[re.Match[str]] = re.search(
            r"<scan:MaxHeight>(\d+)</scan:MaxHeight>",
            capabilities_xml,
        )
        if max_width_match is not None and max_height_match is not None:
            summary["max_width_escl_units"] = int(max_width_match.group(1))
            summary["max_height_escl_units"] = int(max_height_match.group(1))

        resolution_tokens: list[str] = re.findall(
            r"<scan:XResolution>(\d+)</scan:XResolution>",
            capabilities_xml,
        )
        if resolution_tokens:
            distinct_dpi: list[int] = sorted({int(token) for token in resolution_tokens})
            summary["supported_dpi"] = distinct_dpi

        color_tokens: list[str] = re.findall(
            r"<scan:ColorMode>(.*?)</scan:ColorMode>",
            capabilities_xml,
        )
        if color_tokens:
            summary["color_modes"] = sorted(set(color_tokens))

        format_tokens: list[str] = re.findall(
            r"<pwg:DocumentFormat>(.*?)</pwg:DocumentFormat>",
            capabilities_xml,
        )
        if format_tokens:
            summary["document_formats"] = sorted(set(format_tokens))

        if not quiet:
            print("  [Capabilities] Successfully queried eSCL XML capabilities:")
            if summary["make_and_model"]:
                print(f"    Make & Model : {summary['make_and_model']}")
            if summary["uuid"]:
                print(f"    Scanner UUID : {summary['uuid']}")
            if summary["max_width_escl_units"] and summary["max_height_escl_units"]:
                print(
                    f"    Platen Range : {summary['max_width_escl_units']} x "
                    f"{summary['max_height_escl_units']} eSCL units (8.50\" x 11.69\" A4/Letter)"
                )
            if summary["supported_dpi"]:
                dpi_labels: str = ", ".join(str(dpi_item) for dpi_item in summary["supported_dpi"])
                print(f"    Supported DPI: {dpi_labels} DPI")
            if summary["color_modes"]:
                print(f"    Color Modes  : {', '.join(summary['color_modes'])}")

    except Exception as query_error:
        summary["error"] = str(query_error)
        if not quiet:
            print(f"  [Error] Could not parse capabilities: {query_error}")

    return summary


def probe_wia_devices(quiet: bool = False) -> tuple[list[WiaDeviceSummary], str]:
    """
    Inspect local Windows Image Acquisition (WIA) USB imaging devices.

    Parameters
    ----------
    quiet : bool, optional
        Suppress console printing when ``True``, by default ``False``.

    Returns
    -------
    tuple[list[WiaDeviceSummary], str]
        List of discovered WIA device summaries and an error string (empty if healthy).
    """
    devices_list: list[WiaDeviceSummary] = []
    error_text: str = ""

    if not quiet:
        print("\n2. Probing Local Windows WIA Subsystem")

    try:
        import win32com.client  # type: ignore

        device_manager: object = win32com.client.Dispatch("WIA.DeviceManager")
        device_infos: object = getattr(device_manager, "DeviceInfos")
        device_count: int = int(getattr(device_infos, "Count", 0))
        if not quiet:
            print(f"  [WIA Devices Detected] {device_count} device(s) registered.")

        device_index: int
        for device_index in range(1, device_count + 1):
            info_object: object = device_infos.Item(device_index)  # type: ignore[attr-defined]
            properties_object: object = getattr(info_object, "Properties")
            name_property: object = properties_object.Item("Name")  # type: ignore[attr-defined]
            device_name: str = str(getattr(name_property, "Value", "Unknown"))
            device_id: str = str(getattr(info_object, "DeviceID", ""))
            device_type: int = int(getattr(info_object, "Type", 0))
            type_label: str = "Scanner" if device_type == 1 else f"Type {device_type}"

            entry: WiaDeviceSummary = {
                "index": device_index,
                "name": device_name,
                "device_id": device_id,
                "device_type": device_type,
                "type_label": type_label,
            }
            devices_list.append(entry)
            if not quiet:
                print(f"    [{device_index}] {device_name} ({type_label}) — ID: {device_id}")

    except Exception as wia_error:
        error_text = str(wia_error)
        if not quiet:
            print(f"  [Notice] WIA COM probe encountered error: {wia_error}")

    return (devices_list, error_text)


def collect_diagnostics_report(
    host: str = DEFAULT_ESCL_IP,
    port: int = DEFAULT_ESCL_PORT,
    timeout_seconds: float = 3.0,
    save_capabilities_path: Optional[Path] = None,
    quiet: bool = True,
) -> FullDiagnosticsReport:
    """
    Collect a complete wireless eSCL and local WIA hardware diagnostics report.

    Parameters
    ----------
    host : str, optional
        Wireless eSCL host address, by default ``DEFAULT_ESCL_IP``.
    port : int, optional
        Wireless eSCL TCP port, by default ``DEFAULT_ESCL_PORT``.
    timeout_seconds : float, optional
        Probe timeout in seconds, by default ``3.0``.
    save_capabilities_path : Optional[Path], optional
        Optional path to save raw eSCL capabilities XML, by default ``None``.
    quiet : bool, optional
        Suppress console printing when ``True``, by default ``True``.

    Returns
    -------
    FullDiagnosticsReport
        Combined diagnostic dictionary serializable to JSON.
    """
    escl_summary: EsclDiagnosticSummary = probe_escl_scanner(
        host=host,
        port=port,
        timeout_seconds=timeout_seconds,
        save_capabilities_path=save_capabilities_path,
        quiet=quiet,
    )
    wia_result: tuple[list[WiaDeviceSummary], str] = probe_wia_devices(quiet=quiet)
    report: FullDiagnosticsReport = {
        "escl": escl_summary,
        "wia_devices": wia_result[0],
        "wia_error": wia_result[1],
    }
    return report


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Construct the command-line argument parser for ``diagnostics_cli``.

    Returns
    -------
    argparse.ArgumentParser
        Configured diagnostics parser.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="diagnostics_cli",
        description="Scanner Hardware Diagnostics & Network Probe for white-pepper.",
    )
    parser.add_argument(
        "--ip",
        "--host",
        dest="host_ip",
        type=str,
        default=DEFAULT_ESCL_IP,
        help="IPv4 address of wireless eSCL scanner (default: 192.168.1.150).",
    )
    parser.add_argument(
        "--port",
        dest="port_number",
        type=int,
        default=DEFAULT_ESCL_PORT,
        help="HTTP port of wireless eSCL scanner (default: 8080).",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout_seconds",
        type=float,
        default=3.0,
        help="Connection and HTTP read timeout in seconds (default: 3.0).",
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        default=False,
        help="Output structured JSON diagnostics report to stdout.",
    )
    parser.add_argument(
        "--save-capabilities",
        dest="save_capabilities_path",
        type=str,
        default=None,
        help="Filepath to save raw eSCL ScannerCapabilities XML.",
    )
    return parser


def main() -> None:
    """
    Main CLI entry point for ``diagnostics_cli``.

    Returns
    -------
    None
    """
    parser: argparse.ArgumentParser = build_argument_parser()
    arguments: argparse.Namespace = parser.parse_args()

    xml_target: Optional[Path] = (
        Path(str(arguments.save_capabilities_path))
        if arguments.save_capabilities_path
        else None
    )

    if bool(arguments.emit_json):
        report: FullDiagnosticsReport = collect_diagnostics_report(
            host=str(arguments.host_ip),
            port=int(arguments.port_number),
            timeout_seconds=float(arguments.timeout_seconds),
            save_capabilities_path=xml_target,
            quiet=True,
        )
        print(json.dumps(report, indent=2))
        return

    print("--------------------------------------------------")
    print("  white-pepper: Hardware Diagnostics & Device Probe")
    print("--------------------------------------------------\n")
    collect_diagnostics_report(
        host=str(arguments.host_ip),
        port=int(arguments.port_number),
        timeout_seconds=float(arguments.timeout_seconds),
        save_capabilities_path=xml_target,
        quiet=False,
    )
    print("\n[Done] Hardware diagnostic probe completed.")


if __name__ == "__main__":
    main()
