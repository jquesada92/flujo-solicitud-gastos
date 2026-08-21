const delegatedFetch = window.fetch.bind(window);

const state = {
  token: null,
  initialized: false,
  readOnly: false,
  permissionCodes: new Set(),
  refreshPromise: null,
  lastFailedAt: 0,
};

const CONFIG_PREFIXES = [
  '/api/iam',
  '/api/users',
  '/api/rules',
  '/api/areas',
  '/api/categories',
  '/api/audit',
];
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const FAILED_REFRESH_COOLDOWN_MS = 30_000;

function requestPath(input) {
  try {
    const raw = typeof input === 'string' || input instanceof URL
      ? String(input)
      : input.url;
    return new URL(raw, window.location.origin).pathname;
  } catch (_) {
    return '';
  }
}

function requestMethod(input, init = {}) {
  return String(init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
}

function isConfigurationPath(path) {
  return CONFIG_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

window.fetch = async (input, init = {}) => {
  const method = requestMethod(input, init);
  const path = requestPath(input);
  if (state.readOnly && !SAFE_METHODS.has(method) && isConfigurationPath(path)) {
    return new Response(
      JSON.stringify({ detail: 'Tienes acceso de solo lectura a Configuración.' }),
      {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  }
  return delegatedFetch(input, init);
};

function authHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJson(path, { force = false } = {}) {
  const response = await delegatedFetch(path, {
    headers: authHeaders(),
    ...(force ? { cache: 'reload' } : {}),
  });
  if (!response.ok) {
    let detail = 'No se pudo cargar la configuración';
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

function resetMode() {
  state.token = null;
  state.initialized = false;
  state.readOnly = false;
  state.permissionCodes = new Set();
  state.refreshPromise = null;
  document.documentElement.removeAttribute('data-config-readonly');
  closeAccessViewer();
}

async function refreshMode({ force = false } = {}) {
  const token = localStorage.getItem('access_token');
  if (!token) {
    resetMode();
    return;
  }
  if (!force && state.initialized && token === state.token) return;
  if (!force && state.lastFailedAt && Date.now() - state.lastFailedAt < FAILED_REFRESH_COOLDOWN_MS) return;
  if (state.refreshPromise) return state.refreshPromise;

  state.token = token;
  state.refreshPromise = (async () => {
    try {
      const access = await readJson('/api/iam/me/permissions', { force });
      state.permissionCodes = new Set(access.permission_codes || []);
      state.readOnly = state.permissionCodes.has('config:read') && !state.permissionCodes.has('config:manage');
      state.initialized = true;
      state.lastFailedAt = 0;
      if (state.readOnly) {
        document.documentElement.setAttribute('data-config-readonly', 'true');
        applyReadOnlyUi();
      } else {
        document.documentElement.removeAttribute('data-config-readonly');
        closeAccessViewer();
      }
    } catch (_) {
      state.initialized = false;
      state.readOnly = false;
      state.permissionCodes = new Set();
      state.lastFailedAt = Date.now();
      document.documentElement.removeAttribute('data-config-readonly');
    } finally {
      state.refreshPromise = null;
    }
  })();
  return state.refreshPromise;
}

function text(element) {
  return String(element?.textContent || '').trim().toLowerCase();
}

function sectionByHeading(fragment) {
  return [...document.querySelectorAll('main.layout section.card')].find((section) =>
    [...section.querySelectorAll('h2')].some((heading) => text(heading).includes(fragment)),
  );
}

function disableMutationButtons(root) {
  const mutationWords = [
    'guardar', 'crear', 'agregar', 'activar', 'desactivar', 'inactivar',
    'renombrar', 'modificar', 'regenerar', 'eliminar', 'registrar', 'asignar',
  ];
  root?.querySelectorAll('button').forEach((button) => {
    if (mutationWords.some((word) => text(button).includes(word))) button.disabled = true;
  });
}

function addReadOnlyNotice(main) {
  if (!main || main.querySelector('[data-config-readonly-notice="true"]')) return;
  const notice = document.createElement('div');
  notice.dataset.configReadonlyNotice = 'true';
  notice.className = 'notice';
  notice.style.marginBottom = '16px';
  const strong = document.createElement('strong');
  strong.textContent = 'SOLO LECTURA · ';
  const span = document.createElement('span');
  span.textContent = 'Puedes consultar esta configuración, pero no crear, editar, activar, desactivar ni eliminar registros.';
  notice.append(strong, span);
  const hero = main.querySelector('.hero');
  hero?.insertAdjacentElement('afterend', notice);
}

function applyReadOnlyUi() {
  if (!state.readOnly) return;
  const main = document.querySelector('main.layout');
  const title = text(main?.querySelector('.hero h1'));
  const isConfiguration = (
    title.includes('configuración')
    || title.includes('organigrama')
    || title.includes('áreas')
    || title.includes('categorías')
    || title.includes('reglas')
    || title.includes('auditoría')
  );
  if (!main || !isConfiguration) return;
  addReadOnlyNotice(main);

  if (title.includes('usuarios')) {
    const editor = sectionByHeading('crear o modificar usuario');
    if (editor) editor.hidden = true;
  }

  if (title.includes('organigrama')) {
    const assignments = sectionByHeading('asignación de cargos');
    assignments?.querySelectorAll('select').forEach((control) => { control.disabled = true; });
    disableMutationButtons(assignments);
  }

  if (title.includes('áreas') || title.includes('categorías')) {
    const registerSection = [...main.querySelectorAll('section.card')].find((section) =>
      [...section.querySelectorAll('h2')].some((heading) => text(heading).includes('registrar')),
    );
    if (registerSection) registerSection.hidden = true;
    main.querySelectorAll('.catalog-card input, .catalog-card textarea').forEach((control) => { control.disabled = true; });
    main.querySelectorAll('.catalog-card .row-actions button').forEach((button) => { button.disabled = true; });
    main.querySelectorAll('.sub-create').forEach((element) => { element.hidden = true; });
    main.querySelectorAll('.confirm-overlay').forEach((element) => { element.hidden = true; });
    disableMutationButtons(main);
  }

  if (title.includes('reglas')) {
    main.querySelectorAll('.rules-form-card').forEach((section) => { section.hidden = true; });
    main.querySelectorAll('.rules-list-card .row-actions button').forEach((button) => { button.disabled = true; });
    disableMutationButtons(main);
  }
}

function node(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined && value !== null) element.textContent = String(value);
  return element;
}

function accessRow(title, details = [], badge = null) {
  const row = node('div', 'iam-list-item');
  const body = node('span', 'iam-list-main');
  body.appendChild(node('strong', '', title));
  details.filter(Boolean).forEach((detail) => body.appendChild(node('small', '', detail)));
  row.appendChild(body);
  if (badge) row.appendChild(node('span', 'iam-system', badge));
  return row;
}

function closeAccessViewer() {
  document.getElementById('config-readonly-access')?.remove();
}

async function openAccessViewer() {
  await refreshMode();
  if (!state.readOnly) return;

  closeAccessViewer();
  const overlay = node('div', 'iam-overlay');
  overlay.id = 'config-readonly-access';
  const shell = node('main', 'iam-shell');
  const header = node('header', 'iam-header');
  const heading = node('div');
  heading.append(
    node('p', 'iam-eyebrow', 'CONFIGURACIÓN · ACCESOS · SOLO LECTURA'),
    node('h1', '', 'Usuarios, grupos, roles y permisos'),
    node('p', 'iam-muted', 'Modelo de acceso: Usuario → Grupo/Rol → Permisos. Esta vista es informativa.'),
  );
  const actions = node('div', 'iam-actions');
  const close = node('button', 'iam-button primary', 'Volver');
  close.type = 'button';
  close.addEventListener('click', closeAccessViewer);
  actions.appendChild(close);
  header.append(heading, actions);

  const notice = node('div', 'iam-notice', 'SOLO LECTURA · Ningún control de esta vista modifica la configuración.');
  const nav = node('nav', 'iam-tabs');
  const content = node('section', 'iam-card');
  content.appendChild(node('p', 'iam-muted', 'Cargando configuración…'));
  shell.append(header, notice, nav, content);
  overlay.appendChild(shell);
  document.body.appendChild(overlay);

  try {
    const [permissions, roles, groups, users] = await Promise.all([
      readJson('/api/iam/permissions'),
      readJson('/api/iam/roles'),
      readJson('/api/iam/groups'),
      readJson('/api/iam/users'),
    ]);
    const roleById = new Map(roles.map((item) => [item.id, item]));
    const userById = new Map(users.map((item) => [item.id, item]));
    const permissionByCode = new Map(permissions.map((item) => [item.code, item]));

    const tabs = [
      ['users', 'Usuarios'],
      ['groups', 'Grupos'],
      ['roles', 'Roles'],
      ['permissions', 'Permisos'],
    ];
    let active = 'users';

    const render = () => {
      nav.querySelectorAll('button').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === active);
      });
      content.replaceChildren();
      const list = node('div', 'iam-list');
      if (active === 'users') {
        users.forEach((user) => {
          const permissionsText = (user.effective_permission_codes || []).map((code) => permissionByCode.get(code)?.name || code);
          list.appendChild(accessRow(
            user.name,
            [user.email, `Permisos efectivos: ${permissionsText.join(', ') || 'Ninguno'}`],
            user.is_system_account ? 'SISTEMA' : user.active ? 'ACTIVO' : 'INACTIVO',
          ));
        });
      } else if (active === 'groups') {
        groups.forEach((group) => {
          const memberNames = (group.member_ids || []).map((id) => userById.get(id)?.name).filter(Boolean);
          const roleNames = (group.role_ids || []).map((id) => roleById.get(id)?.name).filter(Boolean);
          list.appendChild(accessRow(group.name, [
            group.description || 'Sin descripción',
            `Miembros: ${memberNames.join(', ') || 'Ninguno'}`,
            `Roles: ${roleNames.join(', ') || 'Ninguno'}`,
          ], group.active ? 'ACTIVO' : 'INACTIVO'));
        });
      } else if (active === 'roles') {
        roles.forEach((role) => {
          const labels = (role.permission_codes || []).map((code) => permissionByCode.get(code)?.name || code);
          list.appendChild(accessRow(role.name, [role.description || 'Sin descripción', `Permisos: ${labels.join(', ') || 'Ninguno'}`], role.system_managed ? 'SISTEMA' : role.active ? 'ACTIVO' : 'INACTIVO'));
        });
      } else if (active === 'permissions') {
        permissions.forEach((permission) => {
          list.appendChild(accessRow(permission.name, [permission.code, permission.description || 'Sin descripción'], permission.active ? 'ACTIVO' : 'INACTIVO'));
        });
      }
      if (!list.children.length) list.appendChild(node('p', 'iam-empty', 'No hay registros para mostrar.'));
      content.appendChild(list);
    };

    tabs.forEach(([value, label]) => {
      const button = node('button', '', label);
      button.type = 'button';
      button.dataset.tab = value;
      button.addEventListener('click', () => { active = value; render(); });
      nav.appendChild(button);
    });
    render();
  } catch (error) {
    content.replaceChildren(node('div', 'iam-notice error', error.message));
  }
}

document.addEventListener('click', (event) => {
  const accessButton = event.target.closest?.('[data-iam-access="true"]');
  if (!accessButton) return;
  const menuReadOnly = accessButton.closest('.config-menu-items')?.dataset.configReadonly === 'true';
  if (!state.readOnly && !menuReadOnly) return;
  if (menuReadOnly && !state.readOnly) {
    state.readOnly = true;
    document.documentElement.setAttribute('data-config-readonly', 'true');
    applyReadOnlyUi();
  }
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  openAccessViewer();
}, true);

let refreshScheduled = false;
function scheduleRefreshMode() {
  if (refreshScheduled) return;
  refreshScheduled = true;
  queueMicrotask(() => {
    refreshScheduled = false;
    const token = localStorage.getItem('access_token');
    if (token !== state.token || !state.initialized) refreshMode();
  });
}

const observer = new MutationObserver(() => {
  const menuReadOnly = document.querySelector('.config-menu-items[data-config-readonly="true"]');
  if (menuReadOnly && !state.readOnly) {
    state.readOnly = true;
    document.documentElement.setAttribute('data-config-readonly', 'true');
  }
  if (state.readOnly) applyReadOnlyUi();
  scheduleRefreshMode();
});
observer.observe(document.documentElement, { childList: true, subtree: true });

window.addEventListener('app-auth-changed', () => refreshMode({ force: true }));
window.addEventListener('hashchange', scheduleRefreshMode);
window.addEventListener('focus', scheduleRefreshMode);
window.addEventListener('storage', (event) => {
  if (event.key === 'access_token') refreshMode({ force: true });
});

refreshMode();
