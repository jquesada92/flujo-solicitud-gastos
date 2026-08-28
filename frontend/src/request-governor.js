const delegatedFetch = window.fetch.bind(window);

const inflightReads = new Map();
const recentReads = new Map();
const DEFAULT_READ_TTL_MS = 30_000;
const USER_INTENT_WINDOW_MS = 1_200;
const PROCESSING_OVERLAY_ID = "app-processing-overlay";
const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const BACKGROUND_MUTATION_PATHS = new Set(["/api/auth/activity"]);
const PROCESSING_RELEASE_DELAY_MS = 180;
let lastHumanInteractionAt = 0;
let activeBlockingMutations = 0;
let processingReleaseTimer = null;
let focusBeforeProcessing = null;
let applicationLocked = false;
const inertSnapshots = new Map();

function noteHumanInteraction() {
  lastHumanInteractionAt = Date.now();
}

window.addEventListener("pointerdown", noteHumanInteraction, { passive: true });
window.addEventListener("keydown", noteHumanInteraction, { passive: true });

function requestUrl(input) {
  try {
    const raw = typeof input === "string" || input instanceof URL
      ? String(input)
      : input.url;
    return new URL(raw, window.location.origin);
  } catch (_) {
    return null;
  }
}

function requestMethod(input, init = {}) {
  return String(
    init.method || (input instanceof Request ? input.method : "GET"),
  ).toUpperCase();
}

function requestHeader(input, init, name) {
  const headers = new Headers(
    init.headers || (input instanceof Request ? input.headers : undefined),
  );
  return headers.get(name) || "";
}

function isApiRequest(url) {
  return Boolean(url && url.pathname.startsWith("/api/"));
}

function shouldBlockForMutation(url, method, init) {
  return Boolean(
    isApiRequest(url)
    && MUTATION_METHODS.has(method)
    && init.appMutationOverlay !== false
    && !BACKGROUND_MUTATION_PATHS.has(url.pathname),
  );
}

function processingOverlay() {
  let overlay = document.getElementById(PROCESSING_OVERLAY_ID);
  if (overlay) return overlay;

  overlay = document.createElement("div");
  overlay.id = PROCESSING_OVERLAY_ID;
  overlay.className = "app-processing-overlay";
  overlay.hidden = true;
  overlay.tabIndex = -1;
  overlay.setAttribute("role", "alertdialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-live", "assertive");
  overlay.setAttribute("aria-labelledby", "app-processing-title");
  overlay.setAttribute("aria-describedby", "app-processing-description");
  overlay.innerHTML = `
    <section class="app-processing-card">
      <span class="app-processing-spinner" aria-hidden="true"></span>
      <h2 id="app-processing-title">Procesando…</h2>
      <p id="app-processing-description">Estamos guardando los cambios. Espera un momento.</p>
    </section>
  `;
  document.body.appendChild(overlay);
  return overlay;
}

function lockApplication() {
  if (applicationLocked) return;
  const overlay = processingOverlay();
  applicationLocked = true;
  focusBeforeProcessing = document.activeElement instanceof HTMLElement
    ? document.activeElement
    : null;

  for (const element of document.body.children) {
    if (element === overlay || inertSnapshots.has(element)) continue;
    inertSnapshots.set(element, element.hasAttribute("inert"));
    element.setAttribute("inert", "");
  }

  document.documentElement.setAttribute("data-app-processing", "true");
  document.body.setAttribute("aria-busy", "true");
  overlay.hidden = false;
  overlay.focus({ preventScroll: true });
}

function unlockApplication() {
  if (!applicationLocked) return;
  applicationLocked = false;
  const overlay = document.getElementById(PROCESSING_OVERLAY_ID);
  if (overlay) overlay.hidden = true;

  for (const [element, wasInert] of inertSnapshots) {
    if (!wasInert && element.isConnected) element.removeAttribute("inert");
  }
  inertSnapshots.clear();
  document.documentElement.removeAttribute("data-app-processing");
  document.body.removeAttribute("aria-busy");

  const focusTarget = focusBeforeProcessing;
  focusBeforeProcessing = null;
  if (focusTarget?.isConnected && !focusTarget.hasAttribute("disabled")) {
    focusTarget.focus({ preventScroll: true });
  }
}

function beginBlockingMutation() {
  activeBlockingMutations += 1;
  if (processingReleaseTimer !== null) {
    window.clearTimeout(processingReleaseTimer);
    processingReleaseTimer = null;
  }
  if (activeBlockingMutations === 1) lockApplication();
}

function endBlockingMutation() {
  activeBlockingMutations = Math.max(0, activeBlockingMutations - 1);
  if (activeBlockingMutations > 0) return;

  processingReleaseTimer = window.setTimeout(() => {
    processingReleaseTimer = null;
    if (activeBlockingMutations === 0) unlockApplication();
  }, PROCESSING_RELEASE_DELAY_MS);
}

function isCacheableRead(url, method, init) {
  if (!isApiRequest(url) || !["GET", "HEAD"].includes(method)) return false;
  if (init.cache === "no-store") return false;

  // Authentication and binary/tokenized document endpoints must always reach
  // the server and must never be retained in the in-memory read cache.
  if (url.pathname.startsWith("/api/auth/")) return false;
  if (url.pathname.includes("/attachments/")) return false;
  if (url.pathname.includes("-email/")) return false;
  if (url.pathname.startsWith("/api/approvals/email/")) return false;
  return true;
}

function readKey(input, init, url, method) {
  const authorization = requestHeader(input, init, "Authorization");
  return `${method}:${url.toString()}:auth=${authorization}`;
}

function clearReadCache() {
  recentReads.clear();
}

function pruneExpiredReads(now = Date.now()) {
  for (const [key, entry] of recentReads) {
    if (entry.expiresAt <= now) recentReads.delete(key);
  }
}

window.fetch = async (input, init = {}) => {
  const method = requestMethod(input, init);
  const url = requestUrl(input);
  const blockForMutation = shouldBlockForMutation(url, method, init);
  const delegatedInit = { ...init };
  delete delegatedInit.appMutationOverlay;

  if (isApiRequest(url) && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    // A mutation can change any read model. Drop the short-lived cache before
    // sending it so the next screen load is fresh.
    clearReadCache();
    if (blockForMutation) beginBlockingMutation();
    try {
      return await delegatedFetch(input, delegatedInit);
    } finally {
      if (blockForMutation) endBlockingMutation();
    }
  }

  if (!isCacheableRead(url, method, init)) {
    return delegatedFetch(input, delegatedInit);
  }

  const key = readKey(input, init, url, method);
  const now = Date.now();
  const explicitlyFresh = init.cache === "reload";
  const userInitiated = now - lastHumanInteractionAt <= USER_INTENT_WINDOW_MS;
  pruneExpiredReads(now);

  // A real click/keyboard action is allowed to refresh the server state. The
  // cache is primarily a safety net against automatic effects/polling loops.
  if (!explicitlyFresh && !userInitiated) {
    const cached = recentReads.get(key);
    if (cached && cached.expiresAt > now) {
      return cached.response.clone();
    }
  }

  // Even explicit/user initiated reads share an already-running identical
  // request so one UI action cannot produce duplicate concurrent calls.
  const running = inflightReads.get(key);
  if (running) {
    const response = await running;
    return response.clone();
  }

  const request = delegatedFetch(input, delegatedInit)
    .then((response) => {
      const contentType = response.headers.get("content-type") || "";
      if (response.ok && contentType.includes("application/json")) {
        recentReads.set(key, {
          response: response.clone(),
          expiresAt: Date.now() + DEFAULT_READ_TTL_MS,
        });
      }
      return response;
    })
    .finally(() => inflightReads.delete(key));

  inflightReads.set(key, request);
  const response = await request;
  return response.clone();
};

window.addEventListener("app-auth-changed", clearReadCache);
window.addEventListener("focus", () => pruneExpiredReads());
