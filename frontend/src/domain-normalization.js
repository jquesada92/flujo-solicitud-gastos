const originalFetch = window.fetch.bind(window);

function normalizeRequestUrl(value) {
  const raw = String(value);
  try {
    const parsed = new URL(raw, window.location.origin);
    const path = parsed.pathname;

    if (path === '/api/categories') {
      parsed.pathname = '/api/areas';
    } else {
      let match = path.match(/^\/api\/categories\/subcategories\/(\d+)$/);
      if (match) {
        parsed.pathname = `/api/areas/categories/${match[1]}`;
      } else {
        match = path.match(/^\/api\/categories\/(\d+)\/subcategories$/);
        if (match) {
          parsed.pathname = `/api/areas/${match[1]}/categories`;
        } else {
          match = path.match(/^\/api\/categories\/(\d+)$/);
          if (match) parsed.pathname = `/api/areas/${match[1]}`;
        }
      }
    }

    if (parsed.pathname === '/api/expenses/invoices' && parsed.searchParams.has('category')) {
      parsed.searchParams.set('area', parsed.searchParams.get('category'));
      parsed.searchParams.delete('category');
    }

    return raw.startsWith('http') ? parsed.toString() : `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch (_) {
    return raw;
  }
}

function normalizeExpenseRequestBody(init, normalizedUrl) {
  if (!init || typeof init.body !== 'string') return init;
  try {
    const path = new URL(normalizedUrl, window.location.origin).pathname;
    const isExpenseMutation = path === '/api/expenses' || /^\/api\/expenses\/[^/]+\/resubmit$/.test(path);
    if (!isExpenseMutation) return init;

    const payload = JSON.parse(init.body);
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return init;

    const normalized = { ...payload };
    if ('expense_type' in normalized && !('expense_area' in normalized)) {
      normalized.expense_area = normalized.expense_type;
    }
    if ('expense_subcategory' in normalized && !('expense_category' in normalized)) {
      normalized.expense_category = normalized.expense_subcategory;
    }
    delete normalized.expense_type;
    delete normalized.expense_subcategory;

    return { ...init, body: JSON.stringify(normalized) };
  } catch (_) {
    return init;
  }
}

function adaptLegacyUser(user) {
  if (!user || typeof user !== 'object') return user;
  if (!('person_type' in user) && user.title === 'ADMINISTRADORA') {
    return { ...user, person_type: 'ADMINISTRATOR' };
  }
  return user;
}

function adaptArea(area) {
  if (!area || typeof area !== 'object') return area;
  return {
    ...area,
    subcategories: Array.isArray(area.categories) ? area.categories : area.subcategories || [],
  };
}

function adaptPayload(payload, path) {
  if (path === '/api/areas') {
    return Array.isArray(payload) ? payload.map(adaptArea) : adaptArea(payload);
  }
  if (Array.isArray(payload)) return payload.map((item) => adaptPayload(item, path));
  if (!payload || typeof payload !== 'object') return payload;

  const adapted = Object.fromEntries(
    Object.entries(payload).map(([key, value]) => [key, adaptPayload(value, path)]),
  );

  // API responses are canonical. Keep temporary in-memory aliases only for the
  // remaining legacy React shell until all consumers are migrated.
  if ('expense_area' in adapted && !('expense_type' in adapted)) {
    adapted.expense_type = adapted.expense_area;
  }
  if ('expense_category' in adapted && !('expense_subcategory' in adapted)) {
    adapted.expense_subcategory = adapted.expense_category;
  }

  if ('user' in adapted) adapted.user = adaptLegacyUser(adapted.user);
  if ('title' in adapted && ('role' in adapted || 'email' in adapted)) return adaptLegacyUser(adapted);
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

  const normalizedInit = normalizeExpenseRequestBody(init, normalizedUrl);
  const response = await originalFetch(normalizedInput, normalizedInit);
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return response;

  const path = (() => {
    try { return new URL(normalizedUrl, window.location.origin).pathname; }
    catch (_) { return ''; }
  })();

  const needsAdapter = path === '/api/areas'
    || path.startsWith('/api/auth/')
    || path.startsWith('/api/users')
    || path.startsWith('/api/expenses');
  if (!needsAdapter) return response;

  try {
    const payload = await response.clone().json();
    const adapted = adaptPayload(payload, path);
    return new Response(JSON.stringify(adapted), {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (_) {
    return response;
  }
};

function classificationTerminology(text) {
  if (!text) return text;
  const replacements = {
    '__CATEGORY_PLURAL_CAP__': 'Categorías',
    '__CATEGORY_PLURAL__': 'categorías',
    '__CATEGORY_CAP__': 'Categoría',
    '__CATEGORY__': 'categoría',
  };

  let normalized = String(text)
    .replaceAll('Subcategorías', '__CATEGORY_PLURAL_CAP__')
    .replaceAll('subcategorías', '__CATEGORY_PLURAL__')
    .replaceAll('Subcategoría', '__CATEGORY_CAP__')
    .replaceAll('subcategoría', '__CATEGORY__')
    .replaceAll('Subáreas', '__CATEGORY_PLURAL_CAP__')
    .replaceAll('subáreas', '__CATEGORY_PLURAL__')
    .replaceAll('Subárea', '__CATEGORY_CAP__')
    .replaceAll('subárea', '__CATEGORY__')
    .replaceAll('Categorías', 'Áreas')
    .replaceAll('categorías', 'áreas')
    .replaceAll('Categoría', 'Área')
    .replaceAll('categoría', 'área');

  for (const [token, replacement] of Object.entries(replacements)) {
    normalized = normalized.replaceAll(token, replacement);
  }
  return normalized;
}

function userTerminology(text) {
  if (!text) return text;
  return String(text)
    .replaceAll('Personas', 'Usuarios')
    .replaceAll('personas', 'usuarios')
    .replaceAll('Persona', 'Usuario')
    .replaceAll('persona', 'usuario');
}

function productTerminology(text) {
  return userTerminology(classificationTerminology(text));
}

function isCanonicalTerminologyNode(node) {
  const element = node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
  return Boolean(element?.closest?.('#expense-form, [data-canonical-classification-settings="true"]'));
}

function terminologyForNode(node, text) {
  // Canonical UI already uses Área/Categoría explicitly. The legacy terminology
  // adapter must not rewrite Categoría to Área inside those components.
  return isCanonicalTerminologyNode(node) ? userTerminology(text) : productTerminology(text);
}

function normalizeTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const normalized = terminologyForNode(node, node.nodeValue);
    if (normalized !== node.nodeValue) node.nodeValue = normalized;
  }

  if (root instanceof Element) {
    for (const element of [root, ...root.querySelectorAll('[placeholder], [aria-label], [title]')]) {
      for (const attribute of ['placeholder', 'aria-label', 'title']) {
        if (!element.hasAttribute(attribute)) continue;
        const value = element.getAttribute(attribute);
        const normalized = terminologyForNode(element, value);
        if (normalized !== value) element.setAttribute(attribute, normalized);
      }
    }
  }
}

const observer = new MutationObserver((records) => {
  for (const record of records) {
    for (const node of record.addedNodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        const normalized = terminologyForNode(node, node.nodeValue);
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
