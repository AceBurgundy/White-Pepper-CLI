# White-Pepper Headless Scanner & Vision Engine (`scripts/`)

Standalone, zero-GUI Python scanning, computer vision, and PDF layout toolkit (`v1.1.0`) designed for command-line automation and custom frontend integration.

- **License**: Mozilla Public License 2.0 (`MPL-2.0`)
- **UI Dependency**: Zero (`PyQt6` is never imported in this repository)
- **Protocols**: Wireless eSCL (`AirScan` / `Mopria`), Local Windows WIA COM (`win32com`), and Out-of-Process PowerShell WIA Fallback

---

## 1. Command-Line Entry Points

### A. Hardware Acquisition (`scan_cli.py`)

```powershell
# Preset workflow: 1200 DPI half-platen receipt loop every 15s
python scan_cli.py flatbed boy-gatas-receipts

# ISO A4 office scan at 300 DPI directly to single-page PDF
python scan_cli.py flatbed --paper-size a4 --dpi 300 --color-mode color --format pdf

# Archival 4x6 photo scan at 1200 DPI with custom offset and JPEG export
python scan_cli.py flatbed --paper-size photo-4x6 --dpi 1200 --intent photo --offset-x 10 --offset-y 10 --units mm --format jpg --jpeg-quality 96

# Custom platen region in inches with grayscale, brightness/contrast, and whitespace auto-crop
python scan_cli.py flatbed --paper-size custom --width 6.0 --height 8.0 --units in --dpi 600 --color-mode grayscale --brightness 10 --contrast 15 --auto-crop

# Automated ID-1 card capture with custom corner radius and white background JPEG
python scan_cli.py card --dpi 600 --corner-radius-mm 3.18 --background white --format jpg --no-prompt

# Booklet spread loop (max 12 spreads, 8s page-turn countdown)
python scan_cli.py booklet --paper-size a4 --dpi 300 --interval 8 --max-scans 12
```

#### Supported `--paper-size` Keys
`full`, `a4`, `letter`, `legal` *(clamps safely to 11.69" platen height with notice)*, `a5`, `a6`, `b5`, `executive`, `statement`, `photo-4x6`, `photo-5x7`, `index-3x5`, `id-card`, `receipt-half`, `custom`.

---

### B. Computer Vision & PDF Layout (`process_cli.py`)

```powershell
# Batch extract ID-1 cards with rounded corners onto white JPEG backgrounds
python process_cli.py cards --input-dir D:\Pictures\Scanned\raw_cards --output-dir D:\Pictures\Scanned\cards --dpi 600 --background white --format jpg

# Split booklet spreads (RTL or LTR), auto-orient text via RapidOCR, and export directly to A5 PDF
python process_cli.py booklets --input-dir D:\Pictures\Scanned\dairy_scans --output-dir D:\Pictures\Scanned\pages --reading-direction ltr --compile-pdf D:\Pictures\Scanned\booklet.pdf --pdf-paper-size a5 --pdf-margin-mm 8

# Compile image folder into US Legal or ISO A4 PDF with margins, fit mode, and metadata
python process_cli.py compile-pdf --input-dir D:\Pictures\Scanned\pages --output-file D:\Pictures\Scanned\report.pdf --paper-size a4 --page-orientation portrait --margin-mm 10 --fit-mode contain --jpeg-compression 88 --title "Scanned Report" --author "AceBurgundy"
```

---

### C. Hardware Diagnostics (`diagnostics_cli.py`)

```powershell
# Human-readable network eSCL + local USB WIA probe
python diagnostics_cli.py --ip 192.168.1.150 --port 8080

# Emit machine-readable JSON report and save raw eSCL capabilities XML
python diagnostics_cli.py --json --save-capabilities D:\Pictures\Scanned\caps.xml
```

---

## 2. Programmatic Library Usage

```python
from pathlib import Path
from white_pepper import ScanConfiguration, PdfCompilationConfiguration
from white_pepper.hardware import ScannerManager
from white_pepper.document import compile_pdf_with_config

manager: ScannerManager = ScannerManager(destination_directory=Path(r"D:\Pictures\Scanned"))
scan_config: ScanConfiguration = ScanConfiguration(
    paper_size="a4",
    resolution_dpi=300,
    color_mode="color",
    output_format="png",
)
saved_image: Path = manager.acquire_with_config(scan_config)
```
