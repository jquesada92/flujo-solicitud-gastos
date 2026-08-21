const API_BASE_URL = String(import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const apiUrl = (path) => `${API_BASE_URL}${path}`;

const state = {
  areas: [],
  categories: [],
  selectedAreaId: '',
  assignmentDrafts: {},
  savingAssignmentId: null,
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

function persistedAssignment(category, areaId = state.selectedAreaId) {
  const numericAreaId = Number(areaId);
  return (category.area_ids || []).map(Number).includes(numericAreaId);
}

function resetAssignmentDrafts(areaId = state.selectedAreaId) {
  state.assignmentDrafts = Object.fromEntries(
    state.categories.map((category) => [String(category.id), persistedAssignment(category, areaId)]),
  );
}

function assignmentDraft(category) {
  const key = String(category.id);
  return key in state.assignmentDrafts
    ? Boolean(state.assignmentDrafts[key])
    : persistedAssignment(category);
}

function assignmentChanged(category) {
  return assignmentDraft(category) !== persistedAssignment(category);
}

function visibleAssignmentCategories() {
  return state.categories.filter((category) => category.active);
}

function hasAssignmentChanges() {
  return visibleAssignmentCategories().some(assignmentChanged);
}

async function refreshCatalogs({ resetAssignments = true } = {}) {
  const [areas, categories] = await Promise.all([
    request('/api/areas'),
    request('/api/areas/categories?include_inactive=true'),
  ]);
  state.areas = areas;
  state.categories = categories;
  if (!state.areas.some((item) => String(item.id) === String(state.selectedAreaId))) {
    state.selectedAreaId = String(state.areas.find((item) => item.active)?.id || state.areas[0]?.id || '');
  }
  if (resetAssignments) resetAssignmentDrafts();
}

async function loadData() {
  state.loading = true;
  renderMounted();
  try {
    await refreshCatalogs();
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
    await refreshCatalogs();
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
  let recovery = null;
  input.required = true;
  input.minLength = 2;
  input.maxLength = 150;
  input.placeholder = isArea ? 'Ej. Administración' : 'Ej. Equipo, Insumo o Servicios / Consultoría';
  label.appendChild(input);
  if (isArea) {
    input.addEventListener('input', () => { recovery = null; submit.textContent = 'Crear área'; });
    input.addEventListener('blur', async () => {
      if (input.value.trim().length < 2) return;
      try {
        const candidate = await request(`/api/areas/recovery?name=${encodeURIComponent(input.value.trim())}`);
        if (candidate && window.confirm(`El área “${candidate.name}” ya existe inactiva. ¿Deseas recuperar sus datos?`)) {
          recovery = candidate;
          input.value = candidate.name;
          submit.textContent = 'Reactivar área';
        }
      } catch (error) {
        state.message = { type: 'error', text: error.message };
        renderMounted();
      }
    });
  }
  const submit = node('button', 'primary', isArea ? 'Crear área' : 'Crear categoría');
  submit.type = 'submit';
  form.append(label, submit);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    const path = recovery ? `/api/areas/${recovery.id}` : isArea ? '/api/areas' : '/api/areas/categories';
    await mutate(
      () => request(path, { method: recovery ? 'PATCH' : 'POST', body: JSON.stringify(recovery ? { name, active: true } : { name }) }),
      recovery ? 'Área reactivada correctamente.' : `${isArea ? 'Área' : 'Categoría'} creada correctamente.`,
    );
    input.value = '';
    recovery = null;
    submit.textContent = isArea ? 'Crear área' : 'Crear categoría';
  });
  card.append(form, renderMasterList(isArea ? state.areas : state.categories, kind));
  return card;
}

async function saveAssignment(category) {
  if (!state.selectedAreaId || !assignmentChanged(category)) return;
  const categoryId = String(category.id);
  const assigned = assignmentDraft(category);
  state.savingAssignmentId = categoryId;
  state.message = null;
  renderMounted();
  try {
    const path = `/api/areas/${state.selectedAreaId}/categories/${category.id}`;
    await request(path, { method: assigned ? 'POST' : 'DELETE' });
    await refreshCatalogs();
    state.message = {
      type: 'success',
      text: assigned
        ? `${category.name} fue asignada al área.`
        : `${category.name} fue removida del área.`,
    };
  } catch (error) {
    state.message = { type: 'error', text: error.message };
  } finally {
    state.savingAssignmentId = null;
    renderMounted();
  }
}

function buildAssignmentsTable() {
  const wrap = node('div', 'table-wrap classification-assignment-table-wrap');
  const table = node('table', 'classification-assignment-table');
  const thead = node('thead');
  const headRow = node('tr');
  ['Categoría', 'Asignada', 'Estado', 'Áreas asignadas', 'Acción'].forEach((label) => {
    headRow.appendChild(node('th', '', label));
  });
  thead.appendChild(headRow);

  const tbody = node('tbody');
  visibleAssignmentCategories().forEach((category) => {
    const tr = node('tr');
    const nameCell = node('td');
    nameCell.appendChild(node('strong', '', category.name));

    const assignmentCell = node('td', 'classification-assignment-check-cell');
    const checkbox = node('input');
    checkbox.type = 'checkbox';
    checkbox.setAttribute('aria-label', `Asignar ${category.name}`);
    checkbox.checked = assignmentDraft(category);
    checkbox.disabled = state.loading || Boolean(state.savingAssignmentId);
    checkbox.addEventListener('change', () => {
      state.assignmentDrafts[String(category.id)] = checkbox.checked;
      state.message = null;
      renderMounted();
    });
    assignmentCell.appendChild(checkbox);

    const statusCell = node('td');
    statusCell.appendChild(statusBadge(category.active));

    const countCell = node('td', '', String((category.area_ids || []).length));

    const actionCell = node('td');
    const save = actionButton(
      state.savingAssignmentId === String(category.id) ? 'Guardando...' : 'Guardar',
      'primary classification-save-assignment',
      () => saveAssignment(category),
    );
    save.disabled = !assignmentChanged(category) || Boolean(state.savingAssignmentId);
    actionCell.appendChild(save);

    tr.append(nameCell, assignmentCell, statusCell, countCell, actionCell);
    tbody.appendChild(tr);
  });

  table.append(thead, tbody);
  wrap.appendChild(table);
  return wrap;
}

function buildAssignmentsCard() {
  const card = node('section', 'card classification-assign-card');
  card.append(
    node('p', 'eyebrow', 'ASIGNACIÓN DE CATEGORÍAS'),
    node('h2', '', 'Categorías por área'),
    node('p', 'muted', 'Selecciona un área y define qué categorías activas puede utilizar. Los cambios se guardan por fila, siguiendo el mismo patrón de configuración de perfiles de acceso.'),
  );

  const toolbar = node('div', 'classification-assignment-toolbar');
  const selector = node('label', 'classification-area-selector');
  selector.appendChild(node('span', '', 'Área'));
  const select = node('select');
  state.areas.forEach((area) => {
    const option = node('option', '', `${area.name}${area.active ? '' : ' (inactiva)'}`);
    option.value = String(area.id);
    option.selected = String(area.id) === String(state.selectedAreaId);
    select.appendChild(option);
  });
  select.disabled = !state.areas.length || Boolean(state.savingAssignmentId);
  select.addEventListener('change', () => {
    const nextAreaId = select.value;
    if (hasAssignmentChanges()) {
      const discard = window.confirm('Hay cambios de categorías sin guardar. ¿Deseas descartarlos y cambiar de área?');
      if (!discard) {
        select.value = state.selectedAreaId;
        return;
      }
    }
    state.selectedAreaId = nextAreaId;
    resetAssignmentDrafts(nextAreaId);
    state.message = null;
    renderMounted();
  });
  selector.appendChild(select);
  toolbar.appendChild(selector);

  if (state.areas.length) {
    const activeCategories = visibleAssignmentCategories();
    const dirtyCount = activeCategories.filter(assignmentChanged).length;
    toolbar.appendChild(node(
      'span',
      'filter-count classification-assignment-count',
      dirtyCount ? `${dirtyCount} cambio(s) sin guardar` : `${activeCategories.length} categoría(s)`,
    ));
  }
  card.appendChild(toolbar);

  if (!state.areas.length) {
    card.appendChild(node('p', 'muted', 'Crea al menos un área antes de asignar categorías.'));
    return card;
  }
  if (!state.categories.length) {
    card.appendChild(node('p', 'muted', 'Crea al menos una categoría en el catálogo general.'));
    return card;
  }
  if (!visibleAssignmentCategories().length) {
    card.appendChild(node('p', 'muted', 'No hay categorías activas disponibles para asignar.'));
    return card;
  }

  card.appendChild(buildAssignmentsTable());
  return card;
}

function buildCanonicalUi() {
  const wrapper = node('div', 'classification-canonical');
  wrapper.dataset.canonicalClassificationSettings = 'true';
  const dirtyMarker = node('span');
  dirtyMarker.hidden = true;
  dirtyMarker.dataset.unsaved = hasAssignmentChanges() ? 'true' : 'false';
  wrapper.appendChild(dirtyMarker);
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
  .classification-assignment-toolbar { display:flex; align-items:end; justify-content:space-between; gap:16px; margin:18px 0 14px; }
  .classification-area-selector { flex:1; max-width:520px; margin:0; }
  .classification-assignment-count { white-space:nowrap; padding-bottom:10px; }
  .classification-assignment-table-wrap { margin-top:8px; }
  .classification-assignment-table th:nth-child(2),
  .classification-assignment-table td:nth-child(2),
  .classification-assignment-table th:nth-child(4),
  .classification-assignment-table td:nth-child(4) { text-align:center; }
  .classification-assignment-check-cell input { width:16px; height:16px; }
  .classification-save-assignment { min-width:92px; }
  @media (max-width: 820px) {
    .classification-master-grid { grid-template-columns:1fr; }
    .classification-create-form { grid-template-columns:1fr; }
    .classification-master-row { align-items:flex-start; flex-direction:column; }
    .classification-assignment-toolbar { align-items:stretch; flex-direction:column; }
    .classification-area-selector { max-width:none; }
    .classification-assignment-count { padding-bottom:0; }
  }
`;
document.head.appendChild(styles);

const observer = new MutationObserver(canonicalizeScreen);
observer.observe(document.documentElement, { childList: true, subtree: true });
canonicalizeScreen();
