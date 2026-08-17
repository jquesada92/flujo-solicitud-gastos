// Transitional compatibility layer for the legacy monolithic frontend.
//
// The backend contract now exposes Areas through /api/areas and no longer
// persists property-specific PersonType/Apartment fields. This shim keeps the
// current UI operational while main.jsx is decomposed in a later refactor.
// It contains no business data and can be deleted once main.jsx consumes the
// new Area/User contracts directly.

const originalFetch = window.fetch.bind(window);

function normalizeRequestUrl(value) {
  const raw = String(value);
  let normalized = raw.replaceAll('/api/categories', '/api/areas');

  if (normalized.includes('/api/expenses/invoices') && normalized.includes('category=')) {
    try {
      const parsed = new URL(normalized, window.location.origin);
      if (parsed.searchParams.has('category')) {
        parsed.searchParams.set('area', parsed.searchParams.get('category'));
        parsed.searchParams.delete('category');
      }
      normalized = raw.startsWith('http') ? parsed.toString() : `${parsed.pathname}${parsed.search}${parsed.hash}`;
    } catch (_) {
      // Keep the original normalized URL if parsing fails.
    }
  }

  return normalized;
}

function adaptLegacyUser(user) {
  if (!user || typeof user !== 'object') return user;
  // Compatibility only: authorization remains backend-controlled. This value
  // exists solely because the old UI still checks person_type when deciding
  // whether to render the user-maintenance form.
  if (!('person_type' in user) && user.title === 'ADMINISTRADORA') {
    return { ...user, person_type: 'ADMINISTRATOR' };
  }
  return user;
}

function adaptPayload(payload) {
  if (Array.isArray(payload)) return payload.map(adaptPayload);
  if (!payload || typeof payload !== 'object') return payload;

  const adapted = { ...payload };
  if ('user' in adapted) adapted.user = adaptLegacyUser(adapted.user);
  if ('title' in adapted && ('role' in adapted || 'email' in adapted)) {
    return adaptLegacyUser(adapted);
  }
  return adapted;
}

window.fetch = async (input, init) => {
  const sourceUrl = typeof input === 'string' || input instanceof URL ? String(input) : input.url;
  const normalizedUrl = normalizeRequestUrl(sourceUrl);
  let normalizedInput = input;

  if (typeof input === 'string' || input instanceof URL) {
    normalizedInput = normalizedUrl;
  } else if (normalizedUrl !== sourceUrl) {
    normalizedInput = new Request(normalizedUrl, input);
  }

  const response = await originalFetch(normalizedInput, init);
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return response;

  const path = (() => {
    try { return new URL(normalizedUrl, window.location.origin).pathname; }
    catch (_) { return ''; }
  })();

  const needsUserAdapter = path.startsWith('/api/auth/') || path.startsWith('/api/users');
  if (!needsUserAdapter) return response;

  try {
    const payload = await response.clone().json();
    const adapted = adaptPayload(payload);
    return new Response(JSON.stringify(adapted), {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (_) {
    return response;
  }
};

function areaTerminology(text) {
  if (!text) return text;
  return text
    .replace(/(?<!Sub)Categorías/g, 'Áreas')
    .replace(/(?<!sub)categorías/g, 'áreas')
    .replace(/(?<!Sub)Categoría/g, 'Área')
    .replace(/(?<!sub)categoría/g, 'área');
}

function normalizeTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const normalized = areaTerminology(node.nodeValue);
    if (normalized !== node.nodeValue) node.nodeValue = normalized;
  }

  if (root instanceof Element) {
    for (const element of [root, ...root.querySelectorAll('[placeholder], [aria-label], [title]')]) {
      for (const attribute of ['placeholder', 'aria-label', 'title']) {
        if (!element.hasAttribute(attribute)) continue;
        const value = element.getAttribute(attribute);
        const normalized = areaTerminology(value);
        if (normalized !== value) element.setAttribute(attribute, normalized);
      }
    }
  }
}

const observer = new MutationObserver((records) => {
  for (const record of records) {
    for (const node of record.addedNodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        const normalized = areaTerminology(node.nodeValue);
        if (normalized !== node.nodeValue) node.nodeValue = normalized;
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        normalizeTextNodes(node);
      }
    }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  normalizeTextNodes(document.body);
  observer.observe(document.body, { childList: true, subtree: true });
});
