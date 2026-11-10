/**
 * Navigation item specification: Installation & Windows Installer Guide.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/installation-and-installer-guide.js"] = {
  "item_title": "Installation & Setup",
  "icon_name": "download",
  "header_container": {
    "title": "Windows Installer & Setup Guide",
    "description": "How to install, configure, update, and uninstall White Pepper Scanner Suite and White Pepper CLI Engine on Windows.",
    "badge_list": [
      { "icon_name": "install_desktop", "badge_label": "Inno Setup 6" },
      { "icon_name": "folder", "badge_label": "Custom Install Path" },
      { "icon_name": "delete_forever", "badge_label": "Clean Uninstaller" },
      { "icon_name": "tune", "badge_label": "PATH Integration" }
    ],
    "banner_image": { "image_path": "assets/input.png", "shrink": false },
    "mockup_card": {
      "mockup_title": "Setup Wizard Steps",
      "mockup_options": [
        "1. Select Install Scope (User vs Machine)",
        "2. Choose Custom Destination Directory",
        "3. Optional Desktop & PATH Shortcuts"
      ],
      "mockup_action_buttons": ["Install", "Cancel"]
    }
  },
  "tab_list": [
    {
      "tab_title": "Desktop Suite Setup",
      "icon_name": "desktop_windows",
      "section_blocks": [
        {
          "heading_title": "Using WhitePepper-Desktop-Setup-v1.3.0.exe",
          "block_type": "paragraph",
          "paragraph_text": "The official desktop installer packages the Flutter release application along with the isolated Python scripts and all native runtime assets into an intuitive modern Windows setup wizard."
        },
        {
          "heading_title": "Installer Wizard Flow",
          "block_type": "diamond_list",
          "items": [
            "Scope Selection: Supports both per-user installation (no UAC elevation required, installed to LocalAppData) and all-users installation.",
            "Destination Directory: Users can select any custom folder or drive (e.g., C:\\Program Files\\White Pepper or D:\\Apps\\White Pepper).",
            "Shortcut Customization: Offers optional Start Menu folder creation and a Desktop shortcut checkbox.",
            "Complete Bundle: Automatically includes the scripts/ backend in the installation directory adjacent to the executable."
          ]
        },
        {
          "heading_title": "Clean Uninstallation",
          "block_type": "paragraph",
          "paragraph_text": "White Pepper registers an official uninstaller with Windows. You can uninstall via Windows Settings -> Apps -> Installed Apps, or by running unins000.exe directly in the installation directory. All desktop shortcuts, start menu entries, and cached files are cleanly removed."
        }
      ]
    },
    {
      "tab_title": "CLI Engine Setup",
      "icon_name": "terminal",
      "section_blocks": [
        {
          "heading_title": "Using WhitePepper-CLI-Setup-v1.3.0.exe",
          "block_type": "paragraph",
          "paragraph_text": "For headless environments, automation servers, or developers who only need command-line capabilities, the standalone CLI installer provides quick setup."
        },
        {
          "heading_title": "Command Wrappers in bin/",
          "block_type": "table",
          "table_headers": ["Command", "Script Target", "Description"],
          "table_rows": [
            ["scan-cli", "scan_cli.py", "Execute flatbed, booklet batch, ID card duplex, and legal-stitch scans"],
            ["process-cli", "process_cli.py", "Compile images into multi-page PDF, batch deskew cards, slice booklets"],
            ["diagnostics-cli", "diagnostics_cli.py", "Probe eSCL wireless network endpoints and local USB WIA scanners"],
            ["scan-legal", "scan_legal_two_pass.py", "Interactive two-pass scan orchestrator for 14-inch legal paper"]
          ]
        },
        {
          "heading_title": "Automatic PATH Registration",
          "block_type": "paragraph",
          "paragraph_text": "During installation, checking the 'Add White Pepper CLI to user PATH' task updates your Windows user environment variables. When uninstalled, the uninstaller automatically removes the directory from your PATH."
        },
        {
          "heading_title": "Python Pip Installation Alternative",
          "block_type": "code_block",
          "header_label": "PowerShell / Command Prompt",
          "language_identifier": "bash",
          "code_content": "# Install Python wheel directly\npip install white_pepper_scanner-1.3.0-py3-none-any.whl\n\n# Or install from local source repository\ncd scripts\npip install -r requirements.txt\npip install -e ."
        }
      ]
    }
  ]
};
