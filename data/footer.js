/**
 * Navigation item specification: Application Footer.
 * Configured for White Pepper Scanner Suite, created by AceBurgundy (Sam Adrian P. Sabalo).
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/footer.js"] = {
  "brand_name": "White Pepper Scanner Suite",
  "brand_description": "Created by AceBurgundy (Sam Adrian P. Sabalo). White Pepper pairs a minimalist 4:3 workstation Flutter desktop suite with an isolated headless Python scanning engine, providing lossless optical scanning, eSCL wireless network & USB WIA protocols, dynamic DPI calibration, automated 2-pass legal paper stitching, and clean Windows installers.",
  "social_links": [
    {
      "icon_name": "code",
      "platform_name": "GitHub",
      "url": "https://github.com/AceBurgundy"
    },
    {
      "icon_name": "deployed_code",
      "platform_name": "Flutter Desktop Repo",
      "url": "https://github.com/AceBurgundy/white_pepper"
    },
    {
      "icon_name": "terminal",
      "platform_name": "CLI Engine Repo",
      "url": "https://github.com/AceBurgundy/white_pepper_scripts"
    },
    {
      "icon_name": "mail",
      "platform_name": "Contact",
      "url": "mailto:samadriansabalo99@gmail.com"
    }
  ],
  "columns": [
    {
      "column_title": "Getting Started",
      "links": [
        { "label": "System Architecture", "url": "#/data/navigation-items/overview-and-architecture.js" },
        { "label": "Windows Installer Guide", "url": "#/data/navigation-items/installation-and-installer-guide.js" },
        { "label": "GitHub CI/CD Releases", "url": "#/data/navigation-items/cicd-and-github-releases.js" }
      ]
    },
    {
      "column_title": "Desktop Suite",
      "links": [
        { "label": "4:3 Workstation Layout", "url": "#/data/navigation-items/flutter-desktop-suite.js" },
        { "label": "Options Control Deck", "url": "#/data/navigation-items/flutter-desktop-suite.js" },
        { "label": "Pea Pod Parameter Drawer", "url": "#/data/navigation-items/flutter-desktop-suite.js" },
        { "label": "Platen Preview Canvas", "url": "#/data/navigation-items/flutter-desktop-suite.js" }
      ]
    },
    {
      "column_title": "CLI Engine",
      "links": [
        { "label": "scan_cli Commands", "url": "#/data/navigation-items/headless-cli-engine.js" },
        { "label": "process_cli Batch", "url": "#/data/navigation-items/headless-cli-engine.js" },
        { "label": "diagnostics_cli Probing", "url": "#/data/navigation-items/headless-cli-engine.js" },
        { "label": "2-Pass Legal Stitch CLI", "url": "#/data/navigation-items/headless-cli-engine.js" }
      ]
    },
    {
      "column_title": "Protocols & Vision",
      "links": [
        { "label": "Wireless eSCL XML Protocol", "url": "#/data/navigation-items/hardware-protocols-and-network.js" },
        { "label": "USB WIA & PowerShell", "url": "#/data/navigation-items/hardware-protocols-and-network.js" },
        { "label": "ID Card Vision & Inset", "url": "#/data/navigation-items/card-and-booklet-vision.js" },
        { "label": "DPI Resolution Calibration", "url": "#/data/navigation-items/presets-and-dpi-calibration.js" }
      ]
    },
    {
      "column_title": "Resources",
      "links": [
        { "label": "Desktop GitHub Releases", "url": "https://github.com/AceBurgundy/white_pepper/releases" },
        { "label": "CLI GitHub Releases", "url": "https://github.com/AceBurgundy/white_pepper_scripts/releases" },
        { "label": "eSCL Specifications", "url": "https://mopria.org/escl-specification" }
      ]
    }
  ],
  "legal_links": [
    { "label": "MIT License", "url": "https://github.com/AceBurgundy/white_pepper/blob/main/LICENSE" },
    { "label": "Desktop Repository", "url": "https://github.com/AceBurgundy/white_pepper" },
    { "label": "CLI Submodule", "url": "https://github.com/AceBurgundy/white_pepper_scripts" },
    { "label": "Report Issue", "url": "https://github.com/AceBurgundy/white_pepper/issues" }
  ],
  "copyright_text": "Copyright © 2026 AceBurgundy (Sam Adrian P. Sabalo). Licensed under the MIT License. Built with Flutter Desktop and Python Headless CLI."
};
