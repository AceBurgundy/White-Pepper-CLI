import { Root, Redirect } from "./Component.js";
import { App } from "./components/pages/app/templates/app.js";
import { initializeTheme } from "./common/scripts/theme-manager.js";
import { initializeViewportScaling } from "./common/scripts/viewport-scaler.js";
import documentationData from "./data/data.js";

initializeTheme();
initializeViewportScaling();

/**
 * Root Application Shell factory binding master documentation dataset.
 */
class DocumentedApp extends App {
  constructor() {
    super({ documentationData });
  }
}

// Pre-register routes with the Singleton Redirect router to enable 0ms deep linking
Redirect.register("/", DocumentedApp);
if (documentationData.dashboard_path) {
  Redirect.register(documentationData.dashboard_path, DocumentedApp);
}
if (Array.isArray(documentationData.category_groups)) {
  documentationData.category_groups.forEach((group) => {
    if (Array.isArray(group.navigation_item_paths)) {
      group.navigation_item_paths.forEach((itemPath) => {
        Redirect.register(itemPath, DocumentedApp);
      });
    }
  });
}

new Root({
  destination: DocumentedApp,
  path: "/",
  useHash: "auto",
  persistent: true
}).render();
