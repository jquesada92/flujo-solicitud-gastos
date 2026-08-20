const PROTECTED_HASHES = new Set([
  "#access-management",
  "#user-tracking",
]);

const delegatedFetch = window.fetch.bind(window);
let redirectingToLogin = false;

function requestPath(input) {
  try {
    const raw = typeof input === "string" || input instanceof URL
      ? String(input)
      : input.url;
    return new URL(raw, window.location.origin).pathname;
  } catch (_) {
    return "";
  }
}

function loginLocation() {
  return `${window.location.pathname}${window.location.search}`;
}

function redirectToLogin() {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  localStorage.removeItem("access_token");

  // Protected views are hash-driven overlays. Removing the hash ensures the
  // normal React application owns the next render and shows its Login screen.
  window.history.replaceState(null, document.title, loginLocation());
  window.location.replace(loginLocation());
}

function protectCurrentRoute() {
  if (
    PROTECTED_HASHES.has(window.location.hash)
    && !localStorage.getItem("access_token")
  ) {
    redirectToLogin();
  }
}

window.fetch = async (input, init = {}) => {
  const response = await delegatedFetch(input, init);
  const path = requestPath(input);
  const token = localStorage.getItem("access_token");

  // A 401 while a token exists means the stored session is no longer usable.
  // Do not intercept invalid credentials from the login endpoint itself.
  if (
    response.status === 401
    && token
    && path.startsWith("/api/")
    && path !== "/api/auth/login"
  ) {
    redirectToLogin();
  }

  return response;
};

window.addEventListener("hashchange", protectCurrentRoute);
protectCurrentRoute();
