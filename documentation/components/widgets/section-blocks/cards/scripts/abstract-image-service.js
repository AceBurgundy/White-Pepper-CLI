/**
 * Storage key for persistent card image cache in localStorage.
 * @type {string}
 */
const CARD_IMAGE_CACHE_STORAGE_KEY = "material_dialogs_card_image_cache";

/**
 * In-memory image cache map for fast sub-millisecond retrieval.
 * @type {Map<string, string>}
 */
const inMemoryImageCache = new Map();

/**
 * Loads persistent cache from localStorage into in-memory cache on startup.
 * @returns {void}
 */
function initializePersistentCache() {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    const rawStoredCache = window.localStorage.getItem(CARD_IMAGE_CACHE_STORAGE_KEY);
    if (rawStoredCache) {
      /** @type {Record<string, string>} */
      const parsedStoredCache = JSON.parse(rawStoredCache);
      if (parsedStoredCache && typeof parsedStoredCache === "object") {
        Object.entries(parsedStoredCache).forEach(([cacheKey, imageUrl]) => {
          if (typeof cacheKey === "string" && typeof imageUrl === "string") {
            inMemoryImageCache.set(cacheKey, imageUrl);
          }
        });
      }
    }
  } catch (storageError) {
    console.warn("Could not initialize card image persistent cache from localStorage:", storageError);
  }
}

/**
 * Saves in-memory cache entries back to localStorage.
 * @returns {void}
 */
function persistCacheToStorage() {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    /** @type {Record<string, string>} */
    const cacheObject = {};
    inMemoryImageCache.forEach((imageUrl, cacheKey) => {
      cacheObject[cacheKey] = imageUrl;
    });
    window.localStorage.setItem(CARD_IMAGE_CACHE_STORAGE_KEY, JSON.stringify(cacheObject));
  } catch (storageError) {
    console.warn("Could not persist card image cache to localStorage:", storageError);
  }
}

// Initialize cache from localStorage
initializePersistentCache();

/**
 * Computes a deterministic integer hash from a string identifier.
 * @param {string} inputString - Identifier string (title, link, label).
 * @returns {number} Positive integer hash.
 */
function computeDeterministicHash(inputString) {
  if (!inputString || typeof inputString !== "string") {
    return 1;
  }
  let hashAccumulator = 0;
  for (let characterIndex = 0; characterIndex < inputString.length; characterIndex += 1) {
    const characterCode = inputString.charCodeAt(characterIndex);
    hashAccumulator = ((hashAccumulator << 5) - hashAccumulator) + characterCode;
    hashAccumulator |= 0;
  }
  return Math.abs(hashAccumulator);
}

/**
 * Fallback static asset banner path representing the White Pepper application suite.
 * Replaces external Lorem Picsum CDN requests with localized application assets.
 */
const DEFAULT_FALLBACK_BANNER = "assets/icon.png";

/**
 * Returns a fallback image path within the documentation assets.
 *
 * @param {number|string|null} [_seed=null] - Unused legacy seed.
 * @returns {string} Relative asset image URL.
 */
export function getAbstractImageUrl(_seed = null) {
  return DEFAULT_FALLBACK_BANNER;
}

/**
 * Retrieves a cached image URL for a card, ensuring identical images across page reloads.
 * If an explicit image source is provided, it is returned directly.
 * Otherwise, resolves to localized White Pepper application assets keyed by the card's identifier.
 *
 * @param {string} cardIdentifier - Unique card key (e.g. title, link, or label).
 * @param {string} [explicitSource=""] - Optional explicit image source path or URL.
 * @returns {string} Cached or resolved image URL.
 */
export function getCachedCardImageUrl(cardIdentifier, explicitSource = "") {
  if (explicitSource && typeof explicitSource === "string") {
    return explicitSource;
  }

  const lookupKey = (cardIdentifier || "").toLowerCase();

  if (lookupKey.includes("desktop") || lookupKey.includes("flutter") || lookupKey.includes("workstation")) {
    return "assets/preview_desktop_ui.png";
  }
  if (lookupKey.includes("cli") || lookupKey.includes("headless") || lookupKey.includes("engine") || lookupKey.includes("command")) {
    return "assets/preview_cli_engine.png";
  }
  if (lookupKey.includes("install") || lookupKey.includes("setup") || lookupKey.includes("wizard")) {
    return "assets/preview_installer.png";
  }
  if (lookupKey.includes("hardware") || lookupKey.includes("network") || lookupKey.includes("escl") || lookupKey.includes("wia")) {
    return "assets/hardware_banner.png";
  }
  if (lookupKey.includes("preset") || lookupKey.includes("dpi") || lookupKey.includes("paper")) {
    return "assets/presets_banner.png";
  }
  if (lookupKey.includes("vision") || lookupKey.includes("card") || lookupKey.includes("booklet") || lookupKey.includes("crop")) {
    return "assets/vision_banner.png";
  }
  if (lookupKey.includes("pdf") || lookupKey.includes("document") || lookupKey.includes("export")) {
    return "assets/pdf_banner.png";
  }
  if (lookupKey.includes("cicd") || lookupKey.includes("github") || lookupKey.includes("release")) {
    return "assets/cicd_banner.png";
  }
  if (lookupKey.includes("overview") || lookupKey.includes("architecture")) {
    return "assets/architecture_banner.png";
  }

  return DEFAULT_FALLBACK_BANNER;
}

