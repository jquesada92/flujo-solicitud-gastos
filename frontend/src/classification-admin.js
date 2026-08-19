const API_BASE_URL = String(import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const apiUrl = (path) => `${API_BASE_URL}${path}`;

const state = {
  areas: [],
  categories: [],
  selectedAreaId: '',
  loading: false,
  message: null,
};

function text(value) {
  return String(value || '').trim();
}

function lower(value) {
  return text(value).toLocaleLowerCase('es');
}

function node(tag, className = '', value = null) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== null && value !== undefined) element.textContent = String(value);
  return element;
}

function authHeaders(extra = {}) {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
  if (!response.ok) {
    let detail = 'No se pudo completar la acción';
    try {
      const payload = await response.json();
      detail = typeof payload.detail === 'string' ? payload.detail : detail;
    } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function loadData() {
  state.loading = true;
  renderMounted();
  try {
    const [areas, categories] = await Promise.all([
      request('/api/areas?include_inactive=true'),
      request('/api/areas/categories?include_inactive=true'),
    ]);
    state.areas = areas;
    state.categories = categories;
    if (!state.areas.some((item) => String(item.id) === String(state.selectedAreaId))) {
      state.selectedAreaId = String(state.areas.find((item) => item.active)?.id || state.areas[0]?.id || '');
    }
    state.message = null;
  } catch (error) {
    state.message = { type: 'error', text: error.message };
  } finally {
    state.loading = false;
    renderMounted();
  }
}

async function mutate(action, successText) {
  try {
    await action();
    state.message = { type: 'success', text: successText };
    const [areas, categories] = await Promise.all([
      request('/api/areas?include_inactive=true'),
      request('/api/areas/categories?include_inactive=true'),
    ]);
    state.areas = areas;
    state.categories = categories;
  } catch (error) {
    state.message = { type: 'error', text: error.message };
  }
  renderMounted();
}

function statusBadge(active) {
  return node('span', `catalog-status ${active ? 'active' : 'inactive'}`, active ? 'Activa' : 'Inactiva');
}

function actionButton(label, className, handler) {
  const button = node('button', className, label);
  button.type = 'button';
  button.addEventListener('click', handler);
  return button;
}

function renderMasterList(items, kind) {
  const list = node('div', 'classification-master-list');
  if (!items.length) {
    list.appendChild(node('p', 'muted', kind === 'area' ? 'Aún no hay áreas registradas.' : 'Aún no hay categorías registradas.'));
    return list;
  }
  items.forEach((item) => {
    const row = node('div', `classification-master-row ${item.active ? '' : 'catalog-inactive'}`);
    const body = node('div', 'classification-master-main');
    body.append(node('strong', '', item.name), statusBadge(item.active));
    if (kind === 'category') {
      body.appendChild(node('small', 'subtext', `${(item.area_ids || []).length} área(s) asignada(s)`));
    }
    const actions = node('div', 'row-actions');
    actions.appendChild(actionButton('Renombrar', 'secondary', async () => {
      const next = window.prompt(`Nuevo nombre de ${kind === 'area' ? 'área' : 'categoría'}`, item.name);
      if (!next?.trim() || next.trim() === item.name) return;
      const path = kind === 'area' ? `/api/areas/${item.id}` : `/api/areas/categories/${item.id}`;
      await mutate(
        () => request(path, { method: 'PATCH', body: JSON.stringify({ name: next.trim() }) }),
        `${kind === 'area' ? 'Área' : 'Categoría'} actualizada.`,
      );
    }));
    actions.appendChild(actionButton(item.active ? 'Desactivar' : 'Activar', 'secondary', async () => {
      const path = kind === 'area' ? `/api/areas/${item.id}` : `/api/areas/categories/${item.id}`;
      await mutate(
        () => request(path, { method: 'PATCH', body: JSON.stringify({ active: !item.active }) }),
        `${kind === 'area' ? 'Área' : 'Categoría'} ${item.active ? 'desactivada' : 'activada'}.`,
      );
    }));
    row.append(body, actions);
    list.appendChild(row);
  });
  return list;
}

function buildCreateCard(kind) {
  const isArea = kind === 'area';
  const card = node('section', 'card classification-master-card');
  card.append(
    node('p', 'eyebrow', isArea ? 'MAESTRO DE ÁREAS' : 'MAESTRO DE CATEGORÍAS'),
    node('h2', '', isArea ? 'Áreas' : 'Categorías'),
    node(
      'p',
      'muted',
      isArea
        ? 'Crea las áreas de la organización. Cada área puede reutilizar categorías del catálogo general.'
        : 'Crea cada categoría una sola vez y luego asígnala a una o varias áreas. No se duplican categorías por área.',
    ),
  );

  const form = node('form', 'classification-create-form');
  const label = node('label', '');
  label.appendChild(node('span', '', isArea ? 'Nombre del área' : 'Nombre de la categoría'));
  const input = node('input');
  input.required = true;
  input.minLength = 2;
  input.maxLength = 150;
  input.placeholder = isArea ? 'Ej. Administración' : 'Ej. Equipo, Insumo o Servicios / Consultoría';
  label.appendChild(input);
  const submit = node('button', 'primary', isArea ? 'Crear área' : 'Crear categoría');
  submit.type = 'submit';
  form.append(label, submit);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    const path = isArea ? '/api/areas' : '/api/areas/categories';
    await mutate(
      () => request(path, { method: 'POST', body: JSON.stringify({ name }) }),
      `${isArea ? 'Área' : 'Categoría'} creada correctamente.`,
    );
    input.value = '';
  });
  card.append(form, renderMasterList(isArea ? state.areas : state.categories, kind));
  return card;
}

function buildAssignmentsCard() {
  const card = node('section', 'card classification-assign-card');
  card.append(
    node('p', 'eyebrow', 'RELACIÓN ÁREA → CATEGORÍA'),
    node('h2', '', 'Asignar categorías a las áreas'),
    node('p', 'muted', 'Selecciona un área y habilita las categorías que pueden utilizarse en sus solicitudes. Una categoría puede pertenecer a todas las áreas.'),
  );

  const selector = node('label', 'classification-area-selector');
  selector.appendChild(node('span', '', 'Área'));
  const select = node('select');
  state.areas.forEach((area) => {
    const option = node('option', '', `${area.name}${area.active ? '' : ' (inactiva)'}`);
    option.value = String(area.id);
    option.selected = String(area.id) === String(state.selectedAreaId);
    select.appendChild(option);
  });
  select.disabled = !state.areas.length;
  select.addEventListener('change', () => {
    state.selectedAreaId = select.value;
    renderMounted();
  });
  selector.appendChild(select);
  card.appendChild(selector);

  if (!state.areas.length) {
    card.appendChild(node('p', 'muted', 'Crea al menos un área antes de asignar categorías.'));
    return card;
  }
  if (!state.categories.length) {
    card.appendChild(node('p', 'muted', 'Crea al menos una categoría en el catálogo general.'));
    return card;
  }

  const selectedAreaId = Number(state.selectedAreaId);
  const checks = node('div', 'classification-category-checks');
  state.categories.forEach((category) => {
    const row = node('label', `classification-category-check ${category.active ? '' : 'catalog-inactive'}`);
    const checkbox = node('input');
    checkbox.type = 'checkbox';
    const assigned = (category.area_ids || []).includes(selectedAreaId);
    checkbox.checked = assigned;
    checkbox.disabled = !category.active && !assigned;
    checkbox.addEventListener('change', async () => {
      checkbox.disabled = true;
      const path = `/api/areas/${selectedAreaId}/categories/${category.id}`;
      await mutate(
        () => request(path, { method: checkbox.checked ? 'POST' : 'DELETE' }),
        checkbox.checked
          ? `${category.name} asignada al área.`
          : `${category.name} removida del área.`,
      );
    });
    const copy = node('span', 'classification-category-copy');
    copy.append(node('strong', '', category.name), node('small', 'subtext', category.active ? 'Disponible' : 'Categoría inactiva'));
    row.append(checkbox, copy);
    checks.appendChild(row);
  });
  card.appendChild(checks);
  return card;
}

function buildCanonicalUi() {
  const wrapper = node('div', 'classification-canonical');
  wrapper.dataset.canonicalClassificationSettings = 'true';
  if (state.message) wrapper.appendChild(node('div', `notice ${state.message.type}`, state.message.text));
  if (state.loading) wrapper.appendChild(node('p', 'muted', 'Cargando áreas y categorías…'));

  const grid = node('div', 'classification-master-grid');
  grid.append(buildCreateCard('area'), buildCreateCard('category'));
  wrapper.append(grid, buildAssignmentsCard());
  return wrapper;
}

function mountedContainer() {
  return document.querySelector('[data-canonical-classification-settings="true"]');
}

function renderMounted() {
  const current = mountedContainer();
  if (!current) return;
  current.replaceWith(buildCanonicalUi());
}

function canonicalizeScreen() {
  const main = document.querySelector('main.layout');
  if (!main) return;
  const heroTitle = main.querySelector('.hero h1');
  const title = lower(heroTitle?.textContent);
  const isClassificationScreen = (
    title.includes('categorías y subcategorías')
    || title.includes('areas y categorias')
    || title.includes('áreas y categorías')
  );
  if (!isClassificationScreen) return;

  if (heroTitle && heroTitle.textContent !== 'Áreas y categorías') {
    heroTitle.textContent = 'Áreas y categorías';
  }

  const sections = [...main.querySelectorAll('section.card')];
  const legacyDetails = sections.find((section) => {
    const heading = lower(section.querySelector('h2')?.textContent);
    return heading.includes('categorías y subcategorías') || heading.includes('áreas y categorías');
  });
  if (!legacyDetails) return;
  const legacyRegister = legacyDetails.previousElementSibling?.matches?.('section.card')
    ? legacyDetails.previousElementSibling
    : null;

  if (legacyRegister) legacyRegister.style.display = 'none';
  legacyDetails.style.display = 'none';

  if (!main.querySelector('[data-canonical-classification-settings="true"]')) {
    legacyDetails.insertAdjacentElement('afterend', buildCanonicalUi());
    loadData();
  }
}

const styles = document.createElement('style');
styles.textContent = `
  .classification-master-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; margin-bottom:18px; }
  .classification-master-card { margin:0; }
  .classification-create-form { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:end; margin:18px 0; }
  .classification-create-form label, .classification-area-selector { display:grid; gap:7px; }
  .classification-master-list { display:grid; gap:10px; }
  .classification-master-row { display:flex; align-items:center; justify-content:space-between; gap:14px; padding:12px 0; border-top:1px solid var(--border, #dfe4ec); }
  .classification-master-main { display:grid; gap:5px; min-width:0; }
  .classification-master-main strong { overflow-wrap:anywhere; }
  .classification-master-main .catalog-status { width:max-content; }
  .classification-area-selector { max-width:520px; margin:18px 0; }
  .classification-category-checks { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
  .classification-category-check { display:flex; gap:10px; align-items:flex-start; padding:12px; border:1px solid var(--border, #dfe4ec); border-radius:10px; cursor:pointer; }
  .classification-category-check input { margin-top:4px; }
  .classification-category-copy { display:grid; gap:3px; }
  @media (max-width: 820px) {
    .classification-master-grid, .classification-category-checks { grid-template-columns:1fr; }
    .classification-create-form { grid-template-columns:1fr; }
    .classification-master-row { align-items:flex-start; flex-direction:column; }
  }
`;
document.head.appendChild(styles);

const observer = new MutationObserver(canonicalizeScreen);
observer.observe(document.documentElement, { childList: true, subtree: true });
canonicalizeScreen();
