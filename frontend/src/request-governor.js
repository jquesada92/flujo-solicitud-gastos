const delegatedFetch = window.fetch.bind(window);

const inflightReads = new Map();
const recentReads = new Map();
const DEFAULT_READ_TTL_MS = 30_000;
const USER_INTENT_WINDOW_MS = 1_200;
let lastHumanInteractionAt = 0;

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

  if (isApiRequest(url) && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    // A mutation can change any read model. Drop the short-lived cache before
    // sending it so the next screen load is fresh.
    clearReadCache();
    return delegatedFetch(input, init);
  }

  if (!isCacheableRead(url, method, init)) {
    return delegatedFetch(input, init);
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

  const request = delegatedFetch(input, init)
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
