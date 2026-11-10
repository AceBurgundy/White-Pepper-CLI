/**
 * Navigation item specification: CI/CD & GitHub Releases.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/cicd-and-github-releases.js"] = {
  "item_title": "CI/CD & Releases",
  "icon_name": "rocket_launch",
  "header_container": {
    "title": "CI/CD & Automated GitHub Releases",
    "description": "How GitHub Actions builds, tests, and publishes installers and portable ZIP packages for both repositories on tag push.",
    "badge_list": [
      { "icon_name": "deployed_code", "badge_label": "GitHub Actions" },
      { "icon_name": "sell", "badge_label": "Automated Tagging" },
      { "icon_name": "archive", "badge_label": "Dual Artifacts" }
    ],
    "banner_image": { "image_path": "assets/selection.png", "shrink": false },
    "mockup_card": {
      "mockup_title": "Release Workflow",
      "mockup_options": [
        "1. git tag -a v1.3.0 -m 'Release v1.3.0'",
        "2. GitHub Actions runs test & build",
        "3. Inno Setup compiles release .exe"
      ],
      "mockup_action_buttons": ["Workflow", "Releases"]
    }
  },
  "tab_list": [
    {
      "tab_title": "Desktop Workflow",
      "icon_name": "settings_suggest",
      "section_blocks": [
        {
          "heading_title": "Workflow Specification (.github/workflows/release-desktop.yml)",
          "block_type": "paragraph",
          "paragraph_text": "When a tag like v1.3.0 is pushed to the Flutter desktop repository, GitHub Actions automatically executes the Windows build pipeline."
        },
        {
          "heading_title": "Pipeline Steps",
          "block_type": "diamond_list",
          "items": [
            "Checkout: Clones white_pepper and recursively pulls the standalone scripts submodule.",
            "Static Analysis & Tests: Executes flutter analyze and flutter test across desktop and mobile phone viewport sizes.",
            "Release Build: Compiles the native 64-bit binary with flutter build windows --release.",
            "Inno Setup Compilation: Invokes ISCC.exe on installer/white_pepper_desktop_setup.iss to generate WhitePepper-Desktop-Setup-v1.3.0.exe.",
            "Portable Packaging: Copies scripts/ into the release directory and compresses WhitePepper-Desktop-Portable.zip.",
            "GitHub Release: Attaches both the setup wizard and the portable zip directly to the release draft."
          ]
        },
        {
          "heading_title": "GitHub Actions Workflow Code",
          "block_type": "code_block",
          "header_label": "YAML \u2022 .github/workflows/release-desktop.yml",
          "language_identifier": "yaml",
          "code_content": "name: Release Desktop Suite\non:\n  push:\n    tags: ['v*']\njobs:\n  build-and-release:\n    runs-on: windows-latest\n    steps:\n      - uses: actions/checkout@v4\n        with: { submodules: recursive }\n      - uses: subosito/flutter-action@v2\n        with: { channel: 'stable', cache: true }\n      - run: flutter pub get\n      - run: flutter analyze && flutter test\n      - run: flutter build windows --release\n      - run: '& \"C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe\" installer\\white_pepper_desktop_setup.iss'\n      - uses: softprops/action-gh-release@v2\n        with:\n          files: |\n            installer/output/WhitePepper-Desktop-Setup-*.exe\n            installer/output/WhitePepper-Desktop-Portable.zip"
        }
      ]
    },
    {
      "tab_title": "CLI Workflow",
      "icon_name": "terminal",
      "section_blocks": [
        {
          "heading_title": "Standalone CLI Workflow (.github/workflows/release-cli.yml)",
          "block_type": "paragraph",
          "paragraph_text": "The standalone CLI repository has an independent release cycle. When a tag is pushed to white_pepper_scripts, it compiles the CLI installer and builds standard Python wheels."
        },
        {
          "heading_title": "Published CLI Artifacts",
          "block_type": "table",
          "table_headers": ["Artifact", "Format", "Target Audience"],
          "table_rows": [
            ["WhitePepper-CLI-Setup-v1.3.0.exe", "Inno Setup Executable", "Windows users needing global command wrappers and PATH registration"],
            ["WhitePepper-CLI-Portable.zip", "ZIP Archive", "Portable environments, USB sticks, and temporary workstations"],
            ["white_pepper_scanner-1.3.0-py3-none-any.whl", "Python Wheel", "Python developers, virtual environments, and CI/CD pipelines"],
            ["white_pepper_scanner-1.3.0.tar.gz", "Source Distribution", "Linux, macOS, and custom packaging systems"]
          ]
        }
      ]
    }
  ]
};
