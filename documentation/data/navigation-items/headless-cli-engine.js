/**
 * Navigation item specification: Headless CLI Engine.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/headless-cli-engine.js"] = {
  "item_title": "Headless CLI Engine",
  "icon_name": "terminal",
  "header_container": {
    "title": "Headless CLI Scanning Engine",
    "description": "Comprehensive reference for scan_cli.py, process_cli.py, diagnostics_cli.py, and scan_legal_two_pass.py.",
    "badge_list": [
      { "icon_name": "code", "badge_label": "Python 3.10+" },
      { "icon_name": "settings_input_component", "badge_label": "4 CLI Utilities" },
      { "icon_name": "sync_alt", "badge_label": "JSON IPC Protocol" }
    ],
    "banner_image": { "image_path": "assets/cli_engine_banner.png", "shrink": false },
    "mockup_card": { "image_path": "assets/cli_engine_banner.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "scan_cli.py",
      "icon_name": "scanner",
      "section_blocks": [
        {
          "heading_title": "Core Scan Entrypoint (scan_cli.py)",
          "block_type": "paragraph",
          "paragraph_text": "The primary CLI scanner handles direct acquisition from wireless eSCL endpoints or USB WIA scanners with automated region resolution and post-scan adjustments."
        },
        {
          "heading_title": "Subcommands Reference",
          "block_type": "table",
          "table_headers": ["Subcommand", "Key Arguments", "Description"],
          "table_rows": [
            ["flatbed", "--paper-size, --dpi, --color-mode, --rotate, --auto-crop, --brightness, --contrast, --format, --prefix", "Acquire single flatbed page with optional border trimming"],
            ["card", "--name, --dpi, --color-mode, --background, --safety-inset, --corner-radius, --no-deskew, --no-prompt", "Scan and extract rectangular ID card with rounded corners"],
            ["booklet", "--interval, --max-scans, --dpi, --color-mode, --format, --prefix", "Interactive timer-based booklet page spread acquisition"],
            ["legal-stitch", "--dpi, --color-mode, --format, --ipc-mode, --name", "Orchestrate 2-pass top/bottom scans and stitch into 14-inch legal output"]
          ]
        },
        {
          "heading_title": "Flatbed Command Recipe",
          "block_type": "code_block",
          "header_label": "PowerShell / Bash",
          "language_identifier": "bash",
          "code_content": "# High-resolution 600 DPI A4 scan in PNG format\npython scripts/scan_cli.py flatbed --paper-size a4 --dpi 600 --color-mode color --format png --prefix CONTRACT_2026\n\n# Quick 150 DPI grayscale receipt scan\npython scripts/scan_cli.py flatbed --paper-size receipt-half --dpi 150 --color-mode grayscale --auto-crop"
        }
      ]
    },
    {
      "tab_title": "process_cli.py",
      "icon_name": "auto_fix_high",
      "section_blocks": [
        {
          "heading_title": "Batch Processing & PDF Compilation (process_cli.py)",
          "block_type": "paragraph",
          "paragraph_text": "Handles offline computer vision transformations and document aggregation from previously scanned raster files."
        },
        {
          "heading_title": "Subcommands Reference",
          "block_type": "table",
          "table_headers": ["Subcommand", "Key Arguments", "Description"],
          "table_rows": [
            ["compile-pdf", "--input-directory, --output-pdf, --paper-size, --fit-mode, --resolution, --margin-mm", "Aggregate multiple raster images into a clean multi-page PDF document"],
            ["cards", "--input-directory, --output-directory, --safety-inset, --corner-radius", "Batch detect and deskew card spreads from an input folder"],
            ["booklets", "--input-directory, --output-directory, --cut-percentage", "Split open two-page booklet spreads into individual numbered pages"]
          ]
        },
        {
          "heading_title": "PDF Compilation Command Recipe",
          "block_type": "code_block",
          "header_label": "PowerShell / Bash",
          "language_identifier": "bash",
          "code_content": "# Compile all images in directory to A4 PDF respecting each image's native embedded DPI\npython scripts/process_cli.py compile-pdf --input-directory \"D:\\Pictures\\Scanned\\Batch_01\" --output-pdf \"D:\\Pictures\\Scanned\\Combined.pdf\" --paper-size a4 --fit-mode contain"
        }
      ]
    },
    {
      "tab_title": "diagnostics_cli.py",
      "icon_name": "health_and_safety",
      "section_blocks": [
        {
          "heading_title": "Hardware Probing & Diagnostic Engine",
          "block_type": "paragraph",
          "paragraph_text": "Probes hardware availability without performing a scan. Emits machine-readable JSON for integration into health monitoring dashboards."
        },
        {
          "heading_title": "Diagnostic Output Example",
          "block_type": "code_block",
          "header_label": "JSON Output",
          "language_identifier": "json",
          "code_content": "{\n  \"timestamp\": \"2026-11-10T18:30:00Z\",\n  \"escl_diagnostic\": {\n    \"endpoint_url\": \"http://192.168.1.150:8080/eSCL\",\n    \"is_online\": true,\n    \"model_name\": \"HP DeskJet 4100 series\",\n    \"scanner_state\": \"Idle\",\n    \"supported_dpis\": [75, 100, 200, 300, 600, 1200]\n  },\n  \"wia_devices\": [\n    {\n      \"device_name\": \"HP DeskJet 4100 series\",\n      \"device_id\": \"{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}\\\\0000\",\n      \"is_ready\": true\n    }\n  ]\n}"
        }
      ]
    }
  ]
};
