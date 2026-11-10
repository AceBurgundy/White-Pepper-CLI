/**
 * Navigation item specification: 14 Paper Presets & DPI Calibration.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/presets-and-dpi-calibration.js"] = {
  "item_title": "Presets & Optical DPI",
  "icon_name": "aspect_ratio",
  "header_container": {
    "title": "14 Paper Presets & Optical DPI Calibration",
    "description": "Physical platen geometric clamping, 14 standard paper size specifications, custom millimetre/inch bounds, and optical DPI resolution matrix.",
    "badge_list": [
      { "icon_name": "crop", "badge_label": "14 Standard Presets" },
      { "icon_name": "hd", "badge_label": "75 to 1200 DPI" },
      { "icon_name": "straighten", "badge_label": "Physical Platen Clamping" }
    ],
    "banner_image": { "image_path": "assets/presets_banner.png", "shrink": false },
    "mockup_card": { "image_path": "assets/presets_banner.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "Paper Presets",
      "icon_name": "description",
      "section_blocks": [
        {
          "heading_title": "Platen Physical Clamping",
          "block_type": "paragraph",
          "paragraph_text": "Consumer flatbed scanners (such as the HP DeskJet 4100 series) have a physical platen glass dimension of 8.50 inches wide by 11.693 inches tall (215.9 x 297.0 mm). Any paper specification exceeding the glass dimensions (such as 14.0-inch Legal paper) is automatically clamped to physical hardware boundaries and flagged for software stitching or clipping."
        },
        {
          "heading_title": "Preset Dimensions Table",
          "block_type": "table",
          "table_headers": ["Preset Key", "Name", "Width (mm)", "Height (mm)", "Width (in)", "Height (in)"],
          "table_rows": [
            ["a4", "A4 Document", "210.0", "297.0", "8.27", "11.69"],
            ["letter", "US Letter", "215.9", "279.4", "8.50", "11.00"],
            ["legal", "US Legal (14\")", "215.9", "355.6", "8.50", "14.00"],
            ["a5", "A5 Booklet", "148.0", "210.0", "5.83", "8.27"],
            ["a6", "A6 Postcard", "105.0", "148.0", "4.13", "5.83"],
            ["b5", "B5 Envelope", "176.0", "250.0", "6.93", "9.84"],
            ["photo-4x6", "4x6 Photo", "101.6", "152.4", "4.00", "6.00"],
            ["photo-5x7", "5x7 Portrait", "127.0", "177.8", "5.00", "7.00"],
            ["id-card", "ISO ID-1 Card", "85.6", "54.0", "3.37", "2.13"],
            ["receipt-half", "Half Platen Receipt", "215.9", "148.5", "8.50", "5.85"],
            ["full", "Full Platen Glass", "215.9", "297.0", "8.50", "11.69"]
          ]
        }
      ]
    },
    {
      "tab_title": "Optical DPI Matrix",
      "icon_name": "grid_on",
      "section_blocks": [
        {
          "heading_title": "Optical Resolution Pixel Matrix",
          "block_type": "paragraph",
          "paragraph_text": "Resolutions are clamped to discrete optical stepping points supported by hardware CIS/CCD sensors. Embedded DPI headers are preserved across all raster formats."
        },
        {
          "heading_title": "Resolution Pixel Calculations (Full Platen 8.5 x 11.693\")",
          "block_type": "table",
          "table_headers": ["DPI", "Width (Pixels)", "Height (Pixels)", "Typical Scan Duration", "Recommended Use"],
          "table_rows": [
            ["75 DPI", "638 px", "877 px", "3.5 seconds", "Fast thumbnail preview and layout testing"],
            ["150 DPI", "1,275 px", "1,754 px", "5.0 seconds", "Draft document archiving and email attachments"],
            ["300 DPI", "2,550 px", "3,508 px", "9.0 seconds", "Standard office archival and OCR text recognition"],
            ["600 DPI", "5,100 px", "7,016 px", "24.0 seconds", "High-detail color photography and ID card inspection"],
            ["1200 DPI", "10,200 px", "14,032 px", "65.0 seconds", "Microprint forensics, stamps, and fine line art"]
          ]
        }
      ]
    }
  ]
};
