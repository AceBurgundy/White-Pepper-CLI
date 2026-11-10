/**
 * Navigation item specification: Flutter Desktop Suite UI Architecture.
 */
window.DOCUMENTATION_ITEMS = window.DOCUMENTATION_ITEMS || {};
window.DOCUMENTATION_ITEMS["data/navigation-items/flutter-desktop-suite.js"] = {
  "item_title": "Flutter Desktop Suite",
  "icon_name": "desktop_windows",
  "header_container": {
    "title": "Flutter Desktop Suite & Design System",
    "description": "Deep-dive into the 4:3 workstation container, alternating 2x4 card grid, live platen preview canvas, contoured Pea Pod parameter drawer, and split wavy layout.",
    "badge_list": [
      { "icon_name": "aspect_ratio", "badge_label": "4:3 Workstation Frame" },
      { "icon_name": "palette", "badge_label": "#212121 Onyx Palette" },
      { "icon_name": "touch_app", "badge_label": "Contoured Pea Pod" },
      { "icon_name": "view_in_ar", "badge_label": "Platen Preview" }
    ],
    "banner_image": { "image_path": "assets/prompt.png", "shrink": false },
    "mockup_card": {
      "mockup_title": "UI Component Stack",
      "mockup_options": [
        "1. DashboardScreen (Sidebar & 2x4 Grid)",
        "2. OptionsScreen (Pea Pod & Drawer)",
        "3. InstructionsScreen (Wavy Split View)"
      ],
      "mockup_action_buttons": ["Screens", "Tokens"]
    }
  },
  "tab_list": [
    {
      "tab_title": "Design System",
      "icon_name": "palette",
      "section_blocks": [
        {
          "heading_title": "Minimalist Workstation Aesthetics",
          "block_type": "paragraph",
          "paragraph_text": "The White Pepper desktop interface replicates the precision hardware aesthetic of the minimalist design system: deep onyx charcoal surfaces, intense accent yellow highlights, pill-shaped navigation capsules, and responsive 4:3 workstation framing."
        },
        {
          "heading_title": "Design Tokens & Color Palette",
          "block_type": "table",
          "table_headers": ["Token Name", "Hex Value", "Usage Context"],
          "table_rows": [
            ["DesignTokens.onyx", "#212121", "Primary workstation border, dark deck background, button foreground"],
            ["DesignTokens.accentYellow", "#FFFF1E", "Primary action button, active pill highlights, live LED indicators"],
            ["DesignTokens.neutralLightSurface", "#EEEEEE", "Dashboard background, instruction pane light surface"],
            ["DesignTokens.darkSurfaceOne", "#2A2A2A", "Options screen preview column, console output background"],
            ["DesignTokens.darkSurfaceTwo", "#2D2D2D", "Contoured Pea Pod housing, drawer background, pill clusters"],
            ["DesignTokens.statusOnlineGreen", "#10B981", "Scanner online badge, successful execution checkmarks"]
          ]
        }
      ]
    },
    {
      "tab_title": "Workstation Screens",
      "icon_name": "devices",
      "section_blocks": [
        {
          "heading_title": "Screen 1: Dashboard (DashboardScreen.dart)",
          "block_type": "paragraph",
          "paragraph_text": "The dashboard presents a 310px left sidebar alongside a 2x4 grid of 8 workflow action cards. The sidebar hosts the scanner status card, CMYK ink level bars, and bottom docked navigation pill."
        },
        {
          "heading_title": "Screen 2: Options Control Deck (OptionsScreen.dart)",
          "block_type": "paragraph",
          "paragraph_text": "Opening any workflow transitions smoothly into the dark #212121 Control Deck. The left column displays a 3D Printer Pill capsule with an emerging paper sheet preview that visually rotates and scales according to chosen dimensions. The right column renders the contoured PeaPodWidget with droplet scaling animation and the dynamic parameter drawer."
        },
        {
          "heading_title": "Screen 3: Step-by-Step Instructions (InstructionsScreen.dart)",
          "block_type": "paragraph",
          "paragraph_text": "The instructions screen utilizes an organic cubic-bezier vertical wave divider separating the light physical instruction pane from the dark onyx execution pane. The right pane features an 84x84 circular hold-to-confirm progress trigger button and real-time streaming CLI console output."
        }
      ]
    }
  ]
};
