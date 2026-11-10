/**
 * Navigation item specification: Virtual-Paper PDF Compilation.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/pdf-compilation-and-export.js"] = {
  "item_title": "PDF Compilation & Export",
  "icon_name": "picture_as_pdf",
  "header_container": {
    "title": "Virtual-Paper PDF Compilation Engine",
    "description": "Multi-page PDF generation, automatic embedded image DPI detection, margin bleed controls, and virtual page placement algorithms (contain, fill, stretch, original).",
    "badge_list": [
      { "icon_name": "picture_as_pdf", "badge_label": "ReportLab & Pillow" },
      { "icon_name": "aspect_ratio", "badge_label": "4 Fit Modes" },
      { "icon_name": "auto_awesome", "badge_label": "Automatic DPI Detection" }
    ],
    "banner_image": { "image_path": "assets/scale.png", "shrink": false },
    "mockup_card": {
      "mockup_title": "Fit Modes",
      "mockup_options": [
        "1. contain (Uniform Aspect Ratio Fit)",
        "2. fill (Uniform Crop to Fill Page)",
        "3. original (1:1 Physical Print Size)"
      ],
      "mockup_action_buttons": ["Fit Modes", "Metadata"]
    }
  },
  "tab_list": [
    {
      "tab_title": "Page Fit Modes",
      "icon_name": "crop_free",
      "section_blocks": [
        {
          "heading_title": "Virtual Page Layout Algorithms",
          "block_type": "paragraph",
          "paragraph_text": "When compiling scanned images into a PDF document, the aspect ratio of the scanned region might differ from the destination paper sheet. PdfBuilder provides four distinct fitting strategies:"
        },
        {
          "heading_title": "Fit Mode Comparison",
          "block_type": "table",
          "table_headers": ["Fit Mode", "Aspect Ratio", "Clipping", "Typical Use Case"],
          "table_rows": [
            ["contain (Default)", "Preserved (Uniform)", "No Clipping", "General documents, receipts, contracts (centers image with clean margins)"],
            ["fill", "Preserved (Uniform)", "Clips Edges", "Full-bleed photo books and borderless artwork"],
            ["stretch", "Altered to Fit", "No Clipping", "Legacy forms where coordinates must span exact page boundaries"],
            ["original", "1:1 Physical Size", "Clips if oversized", "Engineering blueprints and architectural scale drawings"]
          ]
        }
      ]
    },
    {
      "tab_title": "Resolution & DPI Headers",
      "icon_name": "hd",
      "section_blocks": [
        {
          "heading_title": "Preserving Embedded DPI Metadata",
          "block_type": "paragraph",
          "paragraph_text": "A common defect in scanning software is discarding DPI metadata and assuming 72 or 96 DPI when compiling to PDF, causing a 600 DPI photo to render as a giant 50-inch poster. White Pepper reads each image's embedded info['dpi'] header: if a page was scanned at 600 DPI, it computes the exact PDF coordinate points (points = pixels * 72 / dpi) so the printed output matches physical paper dimensions with 100% precision."
        },
        {
          "heading_title": "Natural Sorting Sequence",
          "block_type": "paragraph",
          "paragraph_text": "Images are discovered and ordered using natural alphanumeric sorting (natural_sort_key), ensuring that page_1.png, page_2.png, ..., page_10.png are ordered sequentially rather than sorting page_10 before page_2."
        }
      ]
    }
  ]
};
