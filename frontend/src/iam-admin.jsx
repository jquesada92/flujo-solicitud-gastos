import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./iam-admin.css";

const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE_URL}${path}`;

async function iamApi(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = "No se pudo completar la acción";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") message = payload.detail;
    } catch (_) {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

const emptyUser = {
  identity_document: "",
  first_name: "",
  middle_name: "",
  last_name: "",
  second_last_name: "",
  email: "",
  phone: "",
  active: true,
  group_ids: [],
  role_ids: [],
  direct_permission_codes: [],
  position_ids: [],
};

function CheckList({ items, selected, onToggle, getValue = (item) => item.id, render }) {
  const values = new Set(selected || []);
  return (
    <div className="iam-checks">
      {items.map((item) => {
        const value = getValue(item);
        return (
          <label className="iam-check" key={String(value)}>
            <input
              type="checkbox"
              checked={values.has(value)}
              onChange={() => onToggle(value, !values.has(value))}
            />
            <span>{render(item)}</span>
          </label>
        );
      })}
    </div>
  );
}

function PermissionLabel({ permission }) {
  return (
    <>
      <strong>{permission.name}</strong>
      <small>{permission.code}</small>
      {permission.description && <small>{permission.description}</small>}
    </>
  );
}

function RolesPanel({ permissions, roles, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({ name: "", description: "", permission_codes: [] });
  const selected = roles.find((item) => item.id === selectedId) || null;
  const roleDirty = useMemo(() => {
    if (!selected) return Boolean(form.name.trim() || form.description.trim() || form.permission_codes.length);
    const currentPermissions = [...form.permission_codes].map(String).sort();
    const savedPermissions = [...(selected.permission_codes || [])].map(String).sort();
    return (
      form.name !== selected.name
      || form.description !== (selected.description || "")
      || JSON.stringify(currentPermissions) !== JSON.stringify(savedPermissions)
    );
  }, [form, selected]);
  const canPersistRole = roleDirty && form.name.trim().length >= 2;

  useEffect(() => {
    if (selected) {
      setForm({
        name: selected.name,
        description: selected.description || "",
        permission_codes: selected.permission_codes || [],
      });
    } else {
      setForm({ name: "", description: "", permission_codes: [] });
    }
  }, [selectedId, roles.length]);

  const togglePermission = (code, checked) => {
    setForm((current) => ({
      ...current,
      permission_codes: checked
        ? [...new Set([...current.permission_codes, code])]
        : current.permission_codes.filter((item) => item !== code),
    }));
  };

  const save = async (event) => {
    event.preventDefault();
    if (!canPersistRole) return;
    setError("");
    try {
      const body = JSON.stringify({ ...form, active: selected?.active ?? true });
      await iamApi(selected ? `/api/iam/roles/${selected.id}` : "/api/iam/roles", {
        method: selected ? "PATCH" : "POST",
        body,
      });
      setSelectedId(null);
      await reload();
    } catch (error) {
      setError(error.message);
    }
  };

  const toggleActive = async (role) => {
    try {
      await iamApi(`/api/iam/roles/${role.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !role.active }),
      });
      await reload();
    } catch (error) {
      setError(error.message);
    }
  };

  return (
    <div className="iam-grid">
      <section className="iam-card">
        <div className="iam-toolbar"><h2>Roles</h2><button className="iam-button" onClick={() => setSelectedId(null)}>+ Nuevo</button></div>
        <div className="iam-list">
          {roles.map((role) => (
            <div className={`iam-list-item ${selectedId === role.id ? "selected" : ""}`} key={role.id}>
              <button className="iam-button" style={{ textAlign: "left", flex: 1 }} onClick={() => setSelectedId(role.id)}>
                <span className="iam-list-main"><strong>{role.name}</strong><small>{role.permission_codes.join(" · ") || "Sin permisos"}</small></span>
              </button>
              {role.system_managed ? <span className="iam-system">SISTEMA</span> : <button className="iam-button" onClick={() => toggleActive(role)}>{role.active ? "Activo" : "Inactivo"}</button>}
            </div>
          ))}
        </div>
      </section>
      <section className="iam-card">
        <h2>{selected ? `Editar ${selected.name}` : "Crear rol"}</h2>
        {selected?.system_managed ? (
          <div className="iam-notice">Este rol técnico es administrado por el sistema y no puede modificarse desde la interfaz.</div>
        ) : (
          <form className="iam-form" onSubmit={save}>
            <label>Nombre<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} /></label>
            <label>Descripción<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
            <div><strong>Permisos del rol</strong><p className="iam-muted">Los permisos son capacidades del producto; el rol define la combinación que necesita la organización.</p></div>
            <CheckList items={permissions.filter((item) => item.active)} selected={form.permission_codes} getValue={(item) => item.code} onToggle={togglePermission} render={(item) => <PermissionLabel permission={item} />} />
            <button className={`iam-button primary iam-persist-action ${canPersistRole ? "pending" : ""}`} disabled={!canPersistRole}>{selected ? "Guardar cambios" : "Crear rol"}</button>
          </form>
        )}
      </section>
    </div>
  );
}

function GroupsPanel({ groups, roles, users, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [draftRoleIds, setDraftRoleIds] = useState([]);
  const [draftMemberIds, setDraftMemberIds] = useState([]);
  const [savingAssignments, setSavingAssignments] = useState(false);
  const selected = groups.find((item) => item.id === selectedId) || null;

  const normalizeIds = (values) => [...(values || [])].map(Number).sort((a, b) => a - b);
  const groupDirty = useMemo(() => {
    if (!selected) return false;
    return (
      JSON.stringify(normalizeIds(draftRoleIds)) !== JSON.stringify(normalizeIds(selected.role_ids))
      || JSON.stringify(normalizeIds(draftMemberIds)) !== JSON.stringify(normalizeIds(selected.member_ids))
    );
  }, [draftRoleIds, draftMemberIds, selected]);

  useEffect(() => {
    if (selected) {
      setDraftRoleIds([...(selected.role_ids || [])]);
      setDraftMemberIds([...(selected.member_ids || [])]);
    } else {
      setDraftRoleIds([]);
      setDraftMemberIds([]);
    }
  }, [selectedId, selected?.id, JSON.stringify(selected?.role_ids || []), JSON.stringify(selected?.member_ids || [])]);

  const selectGroup = (groupId) => {
    if (groupDirty && !window.confirm("Hay cambios sin guardar en este grupo. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(groupId);
  };

  const createGroup = async (event) => {
    event.preventDefault();
    try {
      await iamApi("/api/iam/groups", { method: "POST", body: JSON.stringify({ name, description, active: true }) });
      setName(""); setDescription(""); await reload();
    } catch (error) { setError(error.message); }
  };
  const patchGroup = async (payload) => {
    try { await iamApi(`/api/iam/groups/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) }); await reload(); }
    catch (error) { setError(error.message); }
  };
  const toggleDraftRole = (roleId, checked) => {
    setDraftRoleIds((current) => checked
      ? [...new Set([...current, roleId])]
      : current.filter((item) => item !== roleId));
  };
  const toggleDraftMember = (userId, checked) => {
    setDraftMemberIds((current) => checked
      ? [...new Set([...current, userId])]
      : current.filter((item) => item !== userId));
  };
  const saveGroupAssignments = async () => {
    if (!selected || !groupDirty || savingAssignments) return;
    setSavingAssignments(true);
    setError("");
    try {
      const savedRoles = new Set(selected.role_ids || []);
      const nextRoles = new Set(draftRoleIds);
      const savedMembers = new Set(selected.member_ids || []);
      const nextMembers = new Set(draftMemberIds);
      const changes = [];

      nextRoles.forEach((roleId) => {
        if (!savedRoles.has(roleId)) changes.push(iamApi(`/api/iam/groups/${selected.id}/roles/${roleId}`, { method: "PUT" }));
      });
      savedRoles.forEach((roleId) => {
        if (!nextRoles.has(roleId)) changes.push(iamApi(`/api/iam/groups/${selected.id}/roles/${roleId}`, { method: "DELETE" }));
      });
      nextMembers.forEach((userId) => {
        if (!savedMembers.has(userId)) changes.push(iamApi(`/api/iam/groups/${selected.id}/members/${userId}`, { method: "PUT" }));
      });
      savedMembers.forEach((userId) => {
        if (!nextMembers.has(userId)) changes.push(iamApi(`/api/iam/groups/${selected.id}/members/${userId}`, { method: "DELETE" }));
      });

      await Promise.all(changes);
      await reload();
    } catch (error) {
      setError(error.message);
    } finally {
      setSavingAssignments(false);
    }
  };

  return (
    <div className="iam-grid">
      <section className="iam-card">
        <h2>Grupos</h2>
        <form className="iam-form" onSubmit={createGroup}>
          <label>Nuevo grupo<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej. Junta Directiva, Finanzas, Procurement" required /></label>
          <label>Descripción<textarea value={description} onChange={(e) => setDescription(e.target.value)} /></label>
          <button className="iam-button primary">Crear grupo</button>
        </form>
        <div className="iam-section iam-list">
          {groups.map((group) => <button key={group.id} className={`iam-list-item ${selectedId === group.id ? "selected" : ""}`} onClick={() => selectGroup(group.id)}><span className="iam-list-main"><strong>{group.name}</strong><small>{group.member_ids.length} usuario(s) · {group.role_ids.length} rol(es)</small></span><span>{group.active ? "Activo" : "Inactivo"}</span></button>)}
        </div>
      </section>
      <section className="iam-card">
        {!selected ? <p className="iam-empty">Selecciona un grupo para administrar sus roles y miembros.</p> : <>
          <span hidden data-unsaved={groupDirty ? "true" : "false"} />
          <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.description || "Sin descripción"}</p></div><button className="iam-button" onClick={() => patchGroup({ active: !selected.active })}>{selected.active ? "Inactivar" : "Activar"}</button></div>
          <div className="iam-toolbar">
            <button className="iam-button" onClick={() => { const value = window.prompt("Nuevo nombre del grupo", selected.name); if (value?.trim()) patchGroup({ name: value.trim() }); }}>Renombrar</button>
            <button
              className={`iam-button primary iam-persist-action ${groupDirty ? "pending" : ""}`}
              disabled={!groupDirty || savingAssignments}
              onClick={saveGroupAssignments}
            >
              {savingAssignments ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
          <div className="iam-section"><h3>Roles heredados por el grupo</h3><CheckList items={roles.filter((item) => item.active && !item.system_managed)} selected={draftRoleIds} onToggle={toggleDraftRole} render={(role) => <><strong>{role.name}</strong><small>{role.permission_codes.join(" · ")}</small></>} /></div>
          <div className="iam-section"><h3>Miembros</h3><CheckList items={users.filter((item) => !item.is_system_account)} selected={draftMemberIds} onToggle={toggleDraftMember} render={(user) => <><strong>{user.name}</strong><small>{user.email}</small></>} /></div>
        </>}
      </section>
    </div>
  );
}

function UsersPanel({ users, groups, roles, permissions, positions, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyUser);
  const selected = users.find((item) => item.id === selectedId) || null;

  const updateAssignment = async (field, value, checked) => {
    const current = selected[field] || [];
    const next = checked ? [...new Set([...current, value])] : current.filter((item) => item !== value);
    try { await iamApi(`/api/iam/users/${selected.id}`, { method: "PATCH", body: JSON.stringify({ [field]: next }) }); await reload(); }
    catch (error) { setError(error.message); }
  };
  const createUser = async (event) => {
    event.preventDefault();
    try {
      await iamApi("/api/iam/users", { method: "POST", body: JSON.stringify(form) });
      setCreating(false); setForm(emptyUser); await reload();
    } catch (error) { setError(error.message); }
  };
  const toggleActive = async () => {
    try { await iamApi(`/api/iam/users/${selected.id}`, { method: "PATCH", body: JSON.stringify({ active: !selected.active }) }); await reload(); }
    catch (error) { setError(error.message); }
  };

  return (
    <div className="iam-grid">
      <section className="iam-card">
        <div className="iam-toolbar"><h2>Usuarios</h2><button className="iam-button" onClick={() => { setCreating(true); setSelectedId(null); }}>+ Usuario</button></div>
        <div className="iam-list">{users.map((user) => <button key={user.id} className={`iam-list-item ${selectedId === user.id ? "selected" : ""}`} onClick={() => { setSelectedId(user.id); setCreating(false); }}><span className="iam-list-main"><strong>{user.name}</strong><small>{user.email}</small></span>{user.is_system_account ? <span className="iam-system">SISTEMA</span> : <span>{user.active ? "Activo" : "Inactivo"}</span>}</button>)}</div>
      </section>
      <section className="iam-card">
        {creating ? <form className="iam-form" onSubmit={createUser}>
          <h2>Crear usuario</h2>
          <div className="iam-two-col"><label>Nombre<input required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label><label>Apellido<input required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label></div>
          <div className="iam-two-col"><label>Segundo nombre<input value={form.middle_name} onChange={(e) => setForm({ ...form, middle_name: e.target.value })} /></label><label>Segundo apellido<input value={form.second_last_name} onChange={(e) => setForm({ ...form, second_last_name: e.target.value })} /></label></div>
          <label>Identificación<input required value={form.identity_document} onChange={(e) => setForm({ ...form, identity_document: e.target.value })} /></label>
          <label>Correo<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label>Teléfono<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <button className="iam-button primary">Crear e invitar</button>
        </form> : !selected ? <p className="iam-empty">Selecciona un usuario o crea uno nuevo.</p> : <>
          <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.email}</p></div>{selected.is_system_account ? <span className="iam-system">CUENTA TÉCNICA PROTEGIDA</span> : <button className="iam-button" onClick={toggleActive}>{selected.active ? "Inactivar" : "Activar"}</button>}</div>
          {selected.is_system_account && <div className="iam-notice">Esta cuenta está separada del flujo financiero. Sus permisos efectivos se limitan a configuración y consulta.</div>}
          {!selected.is_system_account && <>
            <div className="iam-section"><h3>Grupos</h3><CheckList items={groups.filter((item) => item.active)} selected={selected.group_ids} onToggle={(value, checked) => updateAssignment("group_ids", value, checked)} render={(item) => <><strong>{item.name}</strong><small>{item.description || "Grupo de usuarios"}</small></>} /></div>
            <div className="iam-section"><h3>Roles directos</h3><p className="iam-muted">Úsalos solo cuando el acceso no corresponda a un grupo o cargo.</p><CheckList items={roles.filter((item) => item.active && !item.system_managed)} selected={selected.role_ids} onToggle={(value, checked) => updateAssignment("role_ids", value, checked)} render={(item) => <><strong>{item.name}</strong><small>{item.permission_codes.join(" · ")}</small></>} /></div>
            <div className="iam-section"><h3>Permisos individuales</h3><p className="iam-muted">Excepciones ALLOW adicionales. La ausencia de permiso significa DENY salvo capacidades base.</p><CheckList items={permissions.filter((item) => item.active)} selected={selected.direct_permission_codes} getValue={(item) => item.code} onToggle={(value, checked) => updateAssignment("direct_permission_codes", value, checked)} render={(item) => <PermissionLabel permission={item} />} /></div>
            <div className="iam-section"><h3>Cargos</h3><p className="iam-muted">Los cargos pueden heredar roles. Un usuario recibe automáticamente los permisos de los roles asociados a sus cargos.</p><CheckList items={positions.filter((item) => item.active)} selected={selected.position_ids} onToggle={(value, checked) => updateAssignment("position_ids", value, checked)} render={(item) => <><strong>{item.name}</strong><small>{item.role_ids?.length ? `${item.role_ids.length} rol(es) heredado(s)` : item.description || "Cargo organizacional"}</small></>} /></div>
          </>}
          <div className="iam-section"><h3>Permisos efectivos</h3>{selected.effective_permission_codes.length ? selected.effective_permission_codes.map((code) => <div className="iam-permission-row" key={code}><strong>{permissions.find((item) => item.code === code)?.name || code}</strong><code>{code}</code><small>{(selected.permission_sources?.[code] || []).join(" · ")}</small></div>) : <p className="iam-empty">Este usuario no tiene permisos efectivos.</p>}</div>
        </>}
      </section>
    </div>
  );
}

function PositionsPanel({ positions, roles, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const selected = positions.find((item) => item.id === selectedId) || null;

  const create = async (event) => {
    event.preventDefault();
    try {
      await iamApi("/api/iam/positions", { method: "POST", body: JSON.stringify({ name, description, active: true }) });
      setName("");
      setDescription("");
      await reload();
    } catch (error) { setError(error.message); }
  };

  const patch = async (position, payload) => {
    try {
      await iamApi(`/api/iam/positions/${position.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleRole = async (roleId, checked) => {
    try {
      await iamApi(`/api/iam/positions/${selected.id}/roles/${roleId}`, { method: checked ? "PUT" : "DELETE" });
      await reload();
    } catch (error) { setError(error.message); }
  };

  return (
    <div className="iam-grid">
      <section className="iam-card">
        <h2>Crear cargo</h2>
        <form className="iam-form" onSubmit={create}>
          <label>Nombre<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label>Descripción<textarea value={description} onChange={(e) => setDescription(e.target.value)} /></label>
          <button className="iam-button primary">Crear cargo</button>
        </form>
        <div className="iam-section iam-list">
          {positions.map((position) => (
            <button key={position.id} className={`iam-list-item ${selectedId === position.id ? "selected" : ""}`} onClick={() => setSelectedId(position.id)}>
              <span className="iam-list-main"><strong>{position.name}</strong><small>{position.role_ids?.length || 0} rol(es) · {position.description || position.code}</small></span>
              <span>{position.active ? "Activo" : "Inactivo"}</span>
            </button>
          ))}
        </div>
      </section>
      <section className="iam-card">
        {!selected ? <p className="iam-empty">Selecciona un cargo para administrar los roles que heredarán sus usuarios.</p> : <>
          <div className="iam-toolbar">
            <div><h2>{selected.name}</h2><p className="iam-muted">{selected.description || "Cargo organizacional"}</p></div>
            <button className="iam-button" onClick={() => patch(selected, { active: !selected.active })}>{selected.active ? "Inactivar" : "Activar"}</button>
          </div>
          <button className="iam-button" onClick={() => { const value = window.prompt("Nuevo nombre", selected.name); if (value?.trim()) patch(selected, { name: value.trim() }); }}>Renombrar</button>
          <div className="iam-section">
            <h3>Roles heredados por el cargo</h3>
            <p className="iam-muted">Todos los usuarios asignados a este cargo heredarán automáticamente los permisos de estos roles. Los nombres de cargo no están hardcodeados en el sistema.</p>
            <CheckList
              items={roles.filter((item) => item.active && !item.system_managed)}
              selected={selected.role_ids || []}
              onToggle={toggleRole}
              render={(role) => <><strong>{role.name}</strong><small>{role.permission_codes.join(" · ") || "Sin permisos"}</small></>}
            />
          </div>
        </>}
      </section>
    </div>
  );
}

function PermissionsPanel({ permissions }) {
  return <section className="iam-card"><h2>Permisos del producto</h2><p className="iam-muted">Estas son capacidades atómicas implementadas por el producto. La organización configura cómo se combinan mediante roles y cómo esos roles se asignan a usuarios, grupos o cargos.</p><div className="iam-list">{permissions.map((permission) => <div className="iam-list-item" key={permission.code}><span className="iam-list-main"><strong>{permission.name}</strong><small>{permission.code}</small><small>{permission.description}</small></span><span>{permission.active ? "Activo" : "Inactivo"}</span></div>)}</div></section>;
}

function IamConsole() {
  const [tab, setTab] = useState("users");
  const [data, setData] = useState({ permissions: [], roles: [], groups: [], users: [], positions: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = async () => {
    setError("");
    const me = await iamApi("/api/iam/me/permissions");
    if (!me.permission_codes.includes("config:manage")) throw new Error("No tienes permiso para administrar la configuración de accesos");
    const [permissions, roles, groups, users, positions] = await Promise.all([
      iamApi("/api/iam/permissions"), iamApi("/api/iam/roles"), iamApi("/api/iam/groups"), iamApi("/api/iam/users"), iamApi("/api/iam/positions"),
    ]);
    setData({ permissions, roles, groups, users, positions });
  };

  useEffect(() => { reload().catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return undefined;
    const handleTopbarClick = (event) => {
      const target = event.target instanceof Element ? event.target : null;
      const button = target?.closest("button");
      if (!button || !topbar.contains(button)) return;
      if (button.dataset.iamAccess === "true") return;
      if (button.closest(".config-menu") && !button.closest(".config-menu-items")) return;
      window.setTimeout(() => {
        if (window.location.hash === "#access-management") window.location.hash = "";
      }, 0);
    };
    topbar.addEventListener("click", handleTopbarClick);
    return () => topbar.removeEventListener("click", handleTopbarClick);
  }, []);

  if (loading) return <div className="iam-overlay"><main className="iam-shell"><div className="iam-loading">Cargando configuración de accesos…</div></main></div>;
  return <div className="iam-overlay"><main className="iam-shell"><header className="iam-header"><p className="iam-eyebrow">CONFIGURACIÓN · ACCESOS</p><h1>Usuarios, grupos, cargos, roles y permisos</h1><p className="iam-muted">Los permisos efectivos pueden heredarse por grupo o por cargo, además de roles/permisos directos. La estructura y sus nombres son datos configurables.</p></header>{error && <div className="iam-notice error">{error}</div>}<div className="iam-page-nav"><nav className="iam-tabs">{[["users","Usuarios"],["groups","Grupos"],["roles","Roles"],["permissions","Permisos"],["positions","Cargos"]].map(([value,label]) => <button className={tab === value ? "active" : ""} key={value} onClick={() => setTab(value)}>{label}</button>)}</nav><button className="iam-button iam-refresh" onClick={() => reload().catch((e) => setError(e.message))}>↻ Recargar</button></div>{tab === "users" && <UsersPanel {...data} reload={reload} setError={setError} />}{tab === "groups" && <GroupsPanel {...data} reload={reload} setError={setError} />}{tab === "roles" && <RolesPanel {...data} reload={reload} setError={setError} />}{tab === "permissions" && <PermissionsPanel permissions={data.permissions} />}{tab === "positions" && <PositionsPanel positions={data.positions} roles={data.roles} reload={reload} setError={setError} />}</main></div>;
}

let mounted = false;
let root = null;
function renderForHash() {
  const active = window.location.hash === "#access-management";
  if (active && !mounted) {
    const host = document.createElement("div"); host.id = "iam-admin-root"; document.body.appendChild(host);
    root = createRoot(host); root.render(<IamConsole />); mounted = true;
  } else if (!active && mounted) {
    root?.unmount(); document.getElementById("iam-admin-root")?.remove(); root = null; mounted = false;
  }
}

function injectAccessMenu() {
  document.querySelectorAll(".config-menu-items").forEach((menu) => {
    if (menu.querySelector('[data-iam-access="true"]')) return;
    const button = document.createElement("button");
    button.type = "button"; button.dataset.iamAccess = "true"; button.textContent = "Accesos";
    button.addEventListener("click", () => { window.location.hash = "access-management"; });
    menu.appendChild(button);
  });
}

window.addEventListener("hashchange", renderForHash);
new MutationObserver(injectAccessMenu).observe(document.documentElement, { childList: true, subtree: true });
document.addEventListener("DOMContentLoaded", () => { injectAccessMenu(); renderForHash(); });
