"""Two-Pass Legal Paper Auto-Scanner and Zero-Gradient Computer Vision Stitcher.

Captures US Legal (8.50" x 14.00") documents using standard Letter (8.50" x 11.00")
scanners via a deterministic two-pass acquisition and mathematical stitching algorithm.
Completely eliminates the dark black gradient caused by scanning past physical platen glass.
"""

# DPI = Dots Per Inch
# PDF = Portable Document Format
# BGR = Blue Green Red
# RGB = Red Green Blue
# ANSI = American National Standards Institute

from pathlib import Path
import sys
import time
from typing import Optional
import urllib.error

import cv2
import numpy as np
from PIL import Image

# Import White Pepper core modules
from white_pepper.algorithms.legal_vision import (
    LegalStitchResult,
    calculate_legal_dimensions_pixels,
    save_legal_stitch_result_to_pdf,
    stitch_legal_two_pass,
)
from white_pepper.config import ScanConfiguration
from white_pepper.hardware.scanner_manager import ScannerManager


def acquire_raw_letter_scan(
    scanner_manager: ScannerManager,
    temporary_destination_directory: Path,
    resolution_dpi: int,
    pass_label: str,
    color_mode: str = "color",
) -> Path:
    """Acquire a raw Letter scan from the hardware with retry handling.

    Parameters
    ----------
    scanner_manager : ScannerManager
        Initialized White Pepper hardware controller.
    temporary_destination_directory : Path
        Directory to store intermediate raw scan files.
    resolution_dpi : int
        Optical resolution in DPI (300, 600, or 1200).
    pass_label : str
        Label for the pass ('pass1_top' or 'pass2_bottom').
    color_mode : str, optional
        Color mode string ('color', 'grayscale', 'bw'), by default 'color'.

    Returns
    -------
    Path
        Absolute path to the acquired raw image file.

    Raises
    ------
    RuntimeError
        If acquisition fails after maximum retry attempts.
    """
    configuration: ScanConfiguration = ScanConfiguration(
        destination_directory=temporary_destination_directory,
        filename_prefix=f"raw_legal_{pass_label}",
        paper_size_preset="letter",
        resolution_dpi=resolution_dpi,
        color_mode=color_mode,
        output_format="png",
        enable_beep=True,
    )

    maximum_attempts: int = 5
    for attempt_index in range(1, maximum_attempts + 1):
        try:
            acquired_file_path: Path = scanner_manager.acquire_with_config(configuration)
            if acquired_file_path.exists() and acquired_file_path.stat().st_size > 0:
                return acquired_file_path
        except urllib.error.HTTPError as http_exception:
            if http_exception.code == 503 and attempt_index < maximum_attempts:
                print(
                    f"  [Notice] Scanner carriage busy (HTTP 503). Retrying in 3.0s (attempt {attempt_index}/{maximum_attempts})..."
                )
                time.sleep(3.0)
                continue
            raise
        except Exception as general_exception:
            if "503" in str(general_exception) and attempt_index < maximum_attempts:
                print(
                    f"  [Notice] Scanner busy. Retrying in 3.0s (attempt {attempt_index}/{maximum_attempts})..."
                )
                time.sleep(3.0)
                continue
            raise

    raise RuntimeError(f"Failed to acquire raw {pass_label} scan from device.")


def main() -> None:
    """Execute interactive two-pass legal document scanning and stitching."""
    print("=" * 70)
    print("  ZERO-GRADIENT TWO-PASS US LEGAL (8.5\" x 14\") SCANNER & STITCHER")
    print("=" * 70)

    raw_user_input: str = input(
        "\nEnter Document Name (e.g. 'Employment_Contract', 'Affidavit'): "
    ).strip()
    if not raw_user_input:
        print("[Error] No document name provided. Exiting.")
        sys.exit(1)

    has_enclosing_quotes: bool = (
        (raw_user_input.startswith('"') and raw_user_input.endswith('"'))
        or (raw_user_input.startswith("'") and raw_user_input.endswith("'"))
    )

    clean_name: str = raw_user_input.strip("\"'")
    if not has_enclosing_quotes:
        clean_name = clean_name.replace(" ", "_")

    # Resolution selection prompt
    dpi_choice_input: str = input(
        "\nSelect Scan Resolution [300 / 600 / 1200 DPI] (default: 300): "
    ).strip()
    resolution_dpi: int = 300
    if dpi_choice_input in ("300", "600", "1200"):
        resolution_dpi = int(dpi_choice_input)

    output_directory_path: Path = Path(r"D:\Pictures\Scanned\legal")
    output_directory_path.mkdir(parents=True, exist_ok=True)

    temporary_scratch_directory: Path = output_directory_path / "_scratch_legal_raw"
    temporary_scratch_directory.mkdir(parents=True, exist_ok=True)

    destination_pass1_path: Path = temporary_scratch_directory / f"{clean_name}_pass1_top.png"
    destination_pass2_path: Path = temporary_scratch_directory / f"{clean_name}_pass2_bottom.png"
    destination_stitched_png: Path = output_directory_path / f"{clean_name}.png"
    destination_stitched_pdf: Path = output_directory_path / f"{clean_name}.pdf"

    print("\n" + "=" * 70)
    print("  SCAN CONFIGURATION SUMMARY")
    print("=" * 70)
    print(f"  Target Document  : {clean_name}")
    print(f"  Final Size       : US Legal (8.50\" x 14.00\" / 215.9 x 355.6 mm)")
    print(f"  Resolution       : {resolution_dpi} DPI")
    print(f"  Scan Mode        : Two-Pass Letter Clamped (Zero Black Gradient)")
    print(f"  Destination      : {output_directory_path}")
    print("=" * 70)

    scanner_manager: ScannerManager = ScannerManager()

    # Step 1: Upright Top Scan
    if destination_pass1_path.exists():
        reuse_prompt: str = input(
            f"\n[Notice] Existing Pass 1 scan found ({destination_pass1_path.name}).\nUse existing Pass 1 scan? [Y/n]: "
        ).strip().lower()
        if reuse_prompt in ("", "y", "yes"):
            print("  Reusing existing Pass 1 scan.")
        else:
            print("\n[STEP 1 OF 2] Place Legal paper UPRIGHT at the top-left printer markings.")
            print("              (Glass is 100% masked by paper — no black gradient).")
            input(">> Press ENTER when ready to scan PASS 1 (Top)...")
            raw_path_pass1: Path = acquire_raw_letter_scan(
                scanner_manager=scanner_manager,
                temporary_destination_directory=temporary_scratch_directory,
                resolution_dpi=resolution_dpi,
                pass_label="top",
            )
            raw_path_pass1.replace(destination_pass1_path)
    else:
        print("\n[STEP 1 OF 2] Place Legal paper UPRIGHT at the top-left printer markings.")
        print("              (Glass is 100% masked by paper — no black gradient).")
        input(">> Press ENTER when ready to scan PASS 1 (Top)...")
        raw_path_pass1 = acquire_raw_letter_scan(
            scanner_manager=scanner_manager,
            temporary_destination_directory=temporary_scratch_directory,
            resolution_dpi=resolution_dpi,
            pass_label="top",
        )
        raw_path_pass1.replace(destination_pass1_path)

    print(f"  [SAVED] Pass 1 captured: {destination_pass1_path.name}")

    # Step 2: Upside-Down Bottom Scan
    print("\n[STEP 2 OF 2] Rotate paper 180° UPSIDE-DOWN.")
    print("              Align the OPPOSITE CORNER (now the bottom of the document) into the markings.")
    print("              (The bottom of the document is now at the top of the platen glass).")
    input(">> Press ENTER when ready to scan PASS 2 (Bottom)...")

    raw_path_pass2: Path = acquire_raw_letter_scan(
        scanner_manager=scanner_manager,
        temporary_destination_directory=temporary_scratch_directory,
        resolution_dpi=resolution_dpi,
        pass_label="bottom",
    )
    raw_path_pass2.replace(destination_pass2_path)
    print(f"  [SAVED] Pass 2 captured: {destination_pass2_path.name}")

    # Step 3: Stitching
    print("\n[STITCHING] Performing 180° rotation, overlap phase-correlation registration, and geometric cutting...")
    pass1_bgr: np.ndarray = cv2.imread(str(destination_pass1_path))
    pass2_bgr: np.ndarray = cv2.imread(str(destination_pass2_path))

    stitch_result: LegalStitchResult = stitch_legal_two_pass(
        pass1_top_bgr_image=pass1_bgr,
        pass2_bottom_upside_down_bgr_image=pass2_bgr,
        resolution_dpi=resolution_dpi,
        enable_phase_correlation=True,
    )

    print(f"  Registration Confidence : {stitch_result.correlation_confidence * 100:.1f}%")
    print(f"  Detected Horizontal Shift: {stitch_result.horizontal_offset_pixels:+.2f} px")
    print(f"  Detected Vertical Shift  : {stitch_result.vertical_offset_pixels:+.2f} px")
    print(f"  Seam Vertical Position   : Y = {stitch_result.seam_vertical_coordinate_pixels} px")
    print(f"  Final Stitched Dimensions: {stitch_result.stitched_bgr_image.shape[1]}x{stitch_result.stitched_bgr_image.shape[0]} px")

    # Step 4: Save outputs
    print(f"\nSaving final stitched document...")
    # Save PNG via Pillow with embedded DPI
    rgb_stitched: np.ndarray = cv2.cvtColor(stitch_result.stitched_bgr_image, cv2.COLOR_BGR2RGB)
    pil_stitched: Image.Image = Image.fromarray(rgb_stitched)
    pil_stitched.save(destination_stitched_png, "PNG", dpi=(resolution_dpi, resolution_dpi))
    print(f"  [SAVED] High-resolution PNG: {destination_stitched_png}")

    # Save PDF
    save_legal_stitch_result_to_pdf(stitch_result, destination_stitched_pdf)
    print(f"  [SAVED] True-scale Legal PDF : {destination_stitched_pdf}")

    # Cleanup temporary scratch files
    if destination_pass1_path.exists():
        destination_pass1_path.unlink()
    if destination_pass2_path.exists():
        destination_pass2_path.unlink()
    if temporary_scratch_directory.exists() and not any(temporary_scratch_directory.iterdir()):
        temporary_scratch_directory.rmdir()

    print("\n" + "=" * 70)
    print("  TWO-PASS LEGAL SCANNING & STITCHING COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"  Stitched PNG : {destination_stitched_png}")
    print(f"  Stitched PDF : {destination_stitched_pdf}")
    print("=" * 70)


if __name__ == "__main__":
    main()
