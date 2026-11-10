/**
 * Navigation item specification: Hardware Protocols and Network Architecture.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/hardware-protocols-and-network.js"] = {
  "item_title": "Protocols & Network",
  "icon_name": "wifi_tethering",
  "header_container": {
    "title": "Hardware Protocols & Network Communication",
    "description": "How White Pepper negotiates wireless eSCL (Apple AirPrint / Mopria XML) scanning, handles low-power Wi-Fi radio sleep wakeups, and falls back to USB WIA.",
    "badge_list": [
      { "icon_name": "wifi", "badge_label": "eSCL / HTTP XML" },
      { "icon_name": "bedtime", "badge_label": "Radio Sleep Wake Retry" },
      { "icon_name": "usb", "badge_label": "WIA 2.0 COM Bridge" }
    ],
    "banner_image": { "image_path": "assets/hardware_banner.png", "shrink": false },
    "mockup_card": { "image_path": "assets/hardware_banner.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "Wireless eSCL Protocol",
      "icon_name": "wifi",
      "section_blocks": [
        {
          "heading_title": "eSCL XML Specification",
          "block_type": "paragraph",
          "paragraph_text": "eSCL is the driverless network scanning protocol standardized by Mopria and Apple AirPrint. It operates over standard HTTP on port 8080 (or 443 with TLS). White Pepper constructs valid PWG/Scan XML envelopes to configure platen optical resolution and dimensions."
        },
        {
          "heading_title": "eSCL XML Envelope Example",
          "block_type": "code_block",
          "header_label": "XML \u2022 /eSCL/ScanJobs",
          "language_identifier": "xml",
          "code_content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<scan:ScanSettings xmlns:scan=\"http://schemas.hp.com/imaging/escl/2011/01/01\"\n                   xmlns:pwg=\"http://www.pwg.org/schemas/2010/12/sm\">\n  <pwg:Version>2.0</pwg:Version>\n  <pwg:ScanRegions>\n    <pwg:ScanRegion>\n      <pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>\n      <pwg:XOffset>0</pwg:XOffset>\n      <pwg:YOffset>0</pwg:YOffset>\n      <pwg:Width>2550</pwg:Width>\n      <pwg:Height>3508</pwg:Height>\n    </pwg:ScanRegion>\n  </pwg:ScanRegions>\n  <pwg:InputSource>Platen</pwg:InputSource>\n  <scan:ColorMode>RGB24</scan:ColorMode>\n  <scan:XResolution>600</scan:XResolution>\n  <scan:YResolution>600</scan:YResolution>\n  <scan:DocumentFormatExt>image/jpeg</scan:DocumentFormatExt>\n</scan:ScanSettings>"
        },
        {
          "heading_title": "Wi-Fi Low-Power Sleep Mitigation",
          "block_type": "paragraph",
          "paragraph_text": "Wireless multi-function printers routinely power down their Wi-Fi transceivers to conserve power. If a probe request times out after only 2 seconds, standard tools mistakenly assume the scanner is offline and fail. White Pepper's EsclClient implements a 5.0-second wakeup probe with a 2-attempt retry loop and an automated wait_until_idle guard before posting scan jobs."
        }
      ]
    },
    {
      "tab_title": "USB WIA & PowerShell Fallback",
      "icon_name": "usb",
      "section_blocks": [
        {
          "heading_title": "Windows Image Acquisition (WIA) COM Bridge",
          "block_type": "paragraph",
          "paragraph_text": "When a network scanner is not reachable, White Pepper falls back to local USB hardware via Windows Image Acquisition (WIA 2.0). The PowerShell bridge (powershell_bridge.py) interfaces with the WIA COM object model to dynamically configure optical DPI, color intent, and pixel bounding boxes."
        },
        {
          "heading_title": "Protocol Selection Precedence",
          "block_type": "table",
          "table_headers": ["Priority", "Protocol", "Endpoint", "Transport", "Characteristics"],
          "table_rows": [
            ["1 (Primary)", "Wireless eSCL", "http://192.168.1.150:8080/eSCL", "HTTP REST / XML", "Fast, high-fidelity native DPI streaming, driverless"],
            ["2 (Secondary)", "USB WIA 2.0 COM", "WIA.DeviceManager", "Win32 COM Automation", "Direct physical USB transfer, requires Windows WIA driver"],
            ["3 (Tertiary)", "PowerShell Subprocess", "powershell -Command ...", "PowerShell WIA Pipeline", "Fail-safe execution when Python comtypes bindings are unavailable"]
          ]
        }
      ]
    }
  ]
};
