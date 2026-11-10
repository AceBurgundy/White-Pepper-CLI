/**
 * Navigation item specification: Dashboard Landing Page.
 * Auto-generates card blocks connecting all documentation modules for White Pepper.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/dashboard.js"] = {
  "item_title": "Dashboard",
  "icon_name": "dashboard",
  "header_container": {
    "title": "White Pepper Scanner Suite",
    "description": "Unified Windows desktop scanner suite and headless Python automation engine. Engineered with 4:3 workstation aesthetics, eSCL wireless network & USB WIA protocols, discrete optical DPI calibration (75..1200), ID-1 card vision deskew, two-pass legal stitching, and official Windows setup installers.",
    "badge_list": [
      { "icon_name": "desktop_windows", "badge_label": "Flutter 3.x Desktop" },
      { "icon_name": "terminal",        "badge_label": "Python 3.10+ Engine"  },
      { "icon_name": "wifi",            "badge_label": "eSCL / AirPrint XML"  },
      { "icon_name": "usb",             "badge_label": "WIA COM Bridge"      },
      { "icon_name": "verified",        "badge_label": "v1.3.0 Release"       }
    ],
    "banner_image": { "image_path": "assets/icon.png", "shrink": false },
    "mockup_card":  { "image_path": "assets/icon.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "Dashboard",
      "icon_name": "dashboard",
      "section_blocks": [
        {
          "heading_title": "Core System Capabilities",
          "block_type": "cards_container",
          "description": "Explore the multi-layered architecture connecting the Flutter UI workstation to the isolated headless Python hardware engine.",
          "layout_type": "three_cards",
          "cards": [
            {
              "title": "4:3 Workstation Desktop UI",
              "description": "Minimalist onyx layout featuring 8 workflow presets, live platen preview canvas, contoured Pea Pod parameter drawer, and split wavy instructions.",
              "label": "Flutter Desktop",
              "link": "data/navigation-items/flutter-desktop-suite.js"
            },
            {
              "title": "Headless CLI Scanning Engine",
              "description": "Robust Python CLI tools supporting flatbed, booklet batch, ID card extraction, legal two-pass stitch, and virtual-paper PDF compilation.",
              "label": "CLI Architecture",
              "link": "data/navigation-items/headless-cli-engine.js"
            },
            {
              "title": "Windows Setup Installers",
              "description": "Customizable Inno Setup installers with destination folder selection, PATH registration, Desktop shortcuts, and clean Windows uninstallation.",
              "label": "Packaging & Setup",
              "link": "data/navigation-items/installation-and-installer-guide.js"
            }
          ]
        },
        {
          "heading_title": "Hardware & Vision Algorithms",
          "block_type": "cards_container",
          "description": "Deep-dive into network hardware communication, geometric platen clamping, and computer vision routines.",
          "layout_type": "five_cards",
          "cards": [
            {
              "title": "Dual Protocol Communication",
              "description": "Lossless eSCL wireless XML streaming over HTTP port 8080 with automatic fallback to USB Windows Image Acquisition (WIA).",
              "label": "Hardware",
              "link": "data/navigation-items/hardware-protocols-and-network.js"
            },
            {
              "title": "14 Paper Presets & Optical DPI",
              "description": "Discrete optical resolutions from 75 to 1200 DPI with 8.50 x 11.693 physical platen bounds and pixel matrix computation.",
              "label": "Geometry",
              "link": "data/navigation-items/presets-and-dpi-calibration.js"
            },
            {
              "title": "ID-1 Card Vision & Deskew",
              "description": "Canny edge detection, perspective homography transform, safety insets, corner rounding, and alpha compositing.",
              "label": "Computer Vision",
              "link": "data/navigation-items/card-and-booklet-vision.js"
            },
            {
              "title": "Virtual-Paper PDF Engine",
              "description": "Pillow and ReportLab multi-page document compiler with embedded DPI resolution metadata and flexible page placement.",
              "label": "Document Engine",
              "link": "data/navigation-items/pdf-compilation-and-export.js"
            },
            {
              "title": "CI/CD & GitHub Releases",
              "description": "Automated GitHub Actions workflows building release binaries and publishing Inno Setup installers on tag pushes.",
              "label": "DevOps",
              "link": "data/navigation-items/cicd-and-github-releases.js"
            }
          ]
        },
        {
          "heading_title": "Get Started in Minutes",
          "block_type": "cards_container",
          "description": "Set up White Pepper on your workstation using the official installer or run via terminal CLI commands.",
          "layout_type": "two_cards",
          "cards": [
            {
              "title": "Installation & Installer Wizard",
              "description": "Download WhitePepper-Desktop-Setup-v1.3.0.exe or CLI installer with step-by-step setup walkthrough.",
              "label": "Setup Guide",
              "link": "data/navigation-items/installation-and-installer-guide.js"
            },
            {
              "title": "Overview & Architecture Tenets",
              "description": "Explore the isolation model, IPC protocol, and AST-decomposed git repository structure.",
              "label": "Architecture",
              "link": "data/navigation-items/overview-and-architecture.js"
            }
          ]
        }
      ]
    }
  ]
};
