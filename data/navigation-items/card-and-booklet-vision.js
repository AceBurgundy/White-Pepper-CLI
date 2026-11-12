/**
 * Navigation item specification: Card Vision & Legal Stitching.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/card-and-booklet-vision.js"] = {
  "item_title": "Vision & Legal Stitch",
  "icon_name": "visibility",
  "header_container": {
    "title": "Computer Vision & 2-Pass Legal Stitching",
    "description": "ID-1 rectangular card extraction, corner radius masking, safety insets, alpha compositing, booklet spread slicing, and automated two-pass 14-inch legal paper stitching.",
    "badge_list": [
      { "icon_name": "credit_card", "badge_label": "ISO/IEC 7810 ID-1" },
      { "icon_name": "call_merge", "badge_label": "Two-Pass Legal Stitch" },
      { "icon_name": "auto_stories", "badge_label": "Booklet Page Slicing" }
    ],
    "banner_image": { "image_path": "assets/vision_banner.png", "shrink": false },
    "mockup_card": { "image_path": "assets/vision_banner.png", "shrink": false }
  },
  "tab_list": [
    {
      "tab_title": "Card Vision",
      "icon_name": "badge",
      "section_blocks": [
        {
          "heading_title": "ISO/IEC 7810 ID-1 Card Extraction",
          "block_type": "paragraph",
          "paragraph_text": "ID-1 cards (driver licenses, credit cards, national IDs) measure exactly 85.60 x 53.98 mm (3.37 x 2.125 inches) with a 3.18 mm corner radius. CardVision uses OpenCV contour analysis and perspective transformation to extract cards placed at any angle on the platen glass."
        },
        {
          "heading_title": "Card Vision Pipeline",
          "block_type": "diamond_list",
          "items": [
            "Otsu Threshold & Canny Edge Detection: Identifies high-contrast boundaries between the card and the scanner cover.",
            "Rotated Bounding Box & Homography: Aligns the rectangular card to true upright 0-degree orientation.",
            "Safety Inset (0.0 to 3.0 mm): Trims slight optical edge bleed or shadows caused by the scanner glass thickness.",
            "Corner Radius Anti-Aliasing: Generates a 4x supersampled rounded mask matching standard R3.18 mm ISO corners.",
            "Alpha Compositing: Blends the extracted card seamlessly onto transparent, solid white, or onyx dark backgrounds."
          ]
        }
      ]
    },
    {
      "tab_title": "2-Pass Legal Stitch",
      "icon_name": "call_merge",
      "section_blocks": [
        {
          "heading_title": "Overcoming the 11.7-Inch Platen Glass Boundary",
          "block_type": "paragraph",
          "paragraph_text": "Consumer flatbed scanners cannot physically fit a 14.0-inch Legal document in a single pass. White Pepper's Legal 2-Pass Stitching feature solves this hardware limitation without requiring expensive wide-format equipment."
        },
        {
          "heading_title": "Two-Pass Scanning Protocol",
          "block_type": "table",
          "table_headers": ["Pass", "Document Orientation", "Platen Alignment", "Coverage"],
          "table_rows": [
            ["Pass 1 (Top)", "Upright Top", "Top-left glass origin (0, 0)", "Captures inches 0.0 to 11.0 (contains document header and body)"],
            ["Pass 2 (Bottom)", "180-Degree Flipped", "Top-left glass origin (0, 0)", "Captures inches 3.0 to 14.0 (contains document signatures and footer)"]
          ]
        },
        {
          "heading_title": "Alignment & Stitching Algorithm",
          "block_type": "paragraph",
          "paragraph_text": "The LegalStitcher rotates Pass 2 by 180 degrees, normalizes lighting between the two exposures, performs multi-scale template matching across the overlapping ~8.0-inch central region, and applies a linear feathering alpha blend along the seam to produce an exact 14.0-inch Legal document with zero visible seams."
        }
      ]
    }
  ]
};
