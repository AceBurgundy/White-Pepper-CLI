/**
 * Documentation master data registry.
 * Central grouping point for the dashboard landing page, footer, and all category groups.
 * @type {Object}
 */
const documentationData = {
  dashboard_path: "data/dashboard.js",
  footer_path: "data/footer.js",
  category_groups: [
    {
      category_name: "Getting Started",
      navigation_item_paths: [
        "data/navigation-items/overview-and-architecture.js",
        "data/navigation-items/installation-and-installer-guide.js",
        "data/navigation-items/cicd-and-github-releases.js"
      ]
    },
    {
      category_name: "Flutter Desktop Suite",
      navigation_item_paths: [
        "data/navigation-items/flutter-desktop-suite.js",
        "data/navigation-items/presets-and-dpi-calibration.js"
      ]
    },
    {
      category_name: "Headless CLI Engine",
      navigation_item_paths: [
        "data/navigation-items/headless-cli-engine.js",
        "data/navigation-items/hardware-protocols-and-network.js"
      ]
    },
    {
      category_name: "Vision & Processing",
      navigation_item_paths: [
        "data/navigation-items/card-and-booklet-vision.js",
        "data/navigation-items/pdf-compilation-and-export.js"
      ]
    }
  ]
};

export default documentationData;
