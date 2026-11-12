/**
 * Navigation item specification: Overview and System Architecture.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/overview-and-architecture.js"] = {
  "item_title": "Overview & Architecture",
  "icon_name": "account_tree",
  "header_container": {
    "title": "Architecture & System Tenets",
    "description": "Understanding White Pepper's decoupled two-layer system: the Flutter Windows desktop presentation suite and the isolated headless Python hardware engine.",
    "badge_list": [
      { "icon_name": "layers", "badge_label": "Two-Tier Decoupling" },
      { "icon_name": "terminal", "badge_label": "Subprocess CLI IPC" },
      { "icon_name": "speed", "badge_label": "Zero IPC Bottlenecks" }
    ],
    "banner_image": { "image_path": "assets/architecture_banner.png", "shrink": false },
    "mockup_card": { "image_path": "assets/architecture_banner.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "Architecture",
      "icon_name": "schema",
      "section_blocks": [
        {
          "heading_title": "System Topology",
          "block_type": "paragraph",
          "paragraph_text": "White Pepper separates the graphical user experience from low-level physical scanning hardware. Rather than embedding Python in-process with a brittle C-API or shared memory bridges, the Flutter desktop frontend operates as an independent client that orchestrates the Python backend via standardized command-line arguments and asynchronous JSON IPC streaming."
        },
        {
          "heading_title": "Core Architectural Tenets",
          "block_type": "diamond_list",
          "items": [
            "Process Isolation: A crash, hardware timeout, or driver hang in the scanner backend never terminates the desktop GUI.",
            "Independent Lifecycle: The headless Python scripts can be run, scripted, and tested completely independently from terminal or automated cron jobs.",
            "AST Code Decomposition: Both repositories are monitored with granular syntax-tree Git commits (variable -> field -> function -> method -> class -> module -> library).",
            "Single-Executable Installer: Windows Inno Setup packages both layers into an intuitive Windows Setup Wizard."
          ]
        },
        {
          "heading_title": "Process Interaction Graph",
          "block_type": "table",
          "table_headers": ["Component", "Technology", "Responsibility", "Location"],
          "table_rows": [
            ["Desktop Workstation", "Flutter 3.x / Dart", "4:3 workstation GUI, live platen preview canvas, parameter editing", "lib/"],
            ["Command Builder", "Dart Service", "Translates UI parameters into command-line strings (--dpi, --paper-size, etc.)", "lib/services/cli_command_builder.dart"],
            ["Execution Bridge", "Process.start() / Stream", "Spawns Python CLI, streams stdout line-by-line, emits progress events", "lib/services/cli_execution_service.dart"],
            ["Headless Scanning Engine", "Python 3.10+ / OpenCV / PIL", "Physical eSCL XML / WIA transfer, dynamic DPI scaling, card vision, PDF", "scripts/"]
          ]
        }
      ]
    },
    {
      "tab_title": "Workstation Lifecycle",
      "icon_name": "cycle",
      "section_blocks": [
        {
          "heading_title": "The 3-Stage Guided Workflow",
          "block_type": "paragraph",
          "paragraph_text": "White Pepper replaces cluttered multi-window desktop scanner utilities with a focused 3-stage user journey:"
        },
        {
          "heading_title": "Stage Progression",
          "block_type": "table",
          "table_headers": ["Stage", "Screen", "User Actions", "System Response"],
          "table_rows": [
            ["Stage 1: Workstation Dashboard", "DashboardScreen", "Browse 8 workflow cards, review scanner status card and ink gauges", "Polls eSCL scanner endpoint, calculates platen bounds"],
            ["Stage 2: Options Control Deck", "OptionsScreen", "Adjust optical DPI, rotation, color exposure, crop margin in Pea Pod", "Generates live command string preview, renders 3D printer preview"],
            ["Stage 3: Guided Instructions", "InstructionsScreen", "Follow on-screen platen placement diagram, click/hold yellow trigger", "Executes Python subprocess, streams real-time console log, offers Open File/Folder"]
          ]
        }
      ]
    }
  ]
};
