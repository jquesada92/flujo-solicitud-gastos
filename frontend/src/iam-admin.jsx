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
};

const normalizeIds = (values) => [...(values || [])].map(Number).sort((a, b) => a - b);
const sameIds = (left, right) => JSON.stringify(normalizeIds(left)) === JSON.stringify(normalizeIds(right));

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
  return <><strong>{permission.name}</strong><small>{permission.code}</small>{permission.description && <small>{permission.description}</small>}</>;
}

function RolesPanel({ permissions, roles, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({ name: "", description: "", permission_codes: [] });
  const selected = roles.find((item) => item.id === selectedId) || null;
  const roleDirty = useMemo(() => {
    if (!selected) return Boolean(form.name.trim() || form.description.trim() || form.permission_codes.length);
    return (
      form.name !== selected.name
      || form.description !== (selected.description || "")
      || JSON.stringify([...form.permission_codes].sort()) !== JSON.stringify([...(selected.permission_codes || [])].sort())
    );
  }, [form, selected]);
  const canPersistRole = roleDirty && form.name.trim().length >= 2;

  useEffect(() => {
    setForm(selected ? {
      name: selected.name,
      description: selected.description || "",
      permission_codes: selected.permission_codes || [],
    } : { name: "", description: "", permission_codes: [] });
  }, [selectedId, roles]);

  const togglePermission = (code, checked) => setForm((current) => ({
    ...current,
    permission_codes: checked
      ? [...new Set([...current.permission_codes, code])]
      : current.permission_codes.filter((item) => item !== code),
  }));

  const save = async (event) => {
    event.preventDefault();
    if (!canPersistRole) return;
    setError("");
    try {
      await iamApi(selected ? `/api/iam/roles/${selected.id}` : "/api/iam/roles", {
        method: selected ? "PATCH" : "POST",
        body: JSON.stringify({ ...form, active: selected?.active ?? true }),
      });
      setSelectedId(null);
      await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleActive = async (role) => {
    try {
      await iamApi(`/api/iam/roles/${role.id}`, { method: "PATCH", body: JSON.stringify({ active: !role.active }) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  return <div className="iam-grid">
    <section className="iam-card">
      <div className="iam-toolbar"><h2>Roles</h2><button className="iam-button" onClick={() => setSelectedId(null)}>+ Nuevo</button></div>
      <div className="iam-list">{roles.map((role) => <div className={`iam-list-item ${selectedId === role.id ? "selected" : ""}`} key={role.id}>
        <button className="iam-button" style={{ textAlign: "left", flex: 1 }} onClick={() => setSelectedId(role.id)}><span className="iam-list-main"><strong>{role.name}</strong><small>{role.permission_codes.join(" · ") || "Sin permisos"}</small></span></button>
        {role.system_managed ? <span className="iam-system">SISTEMA</span> : <button className="iam-button" onClick={() => toggleActive(role)}>{role.active ? "Activo" : "Inactivo"}</button>}
      </div>)}</div>
    </section>
    <section className="iam-card">
      <h2>{selected ? `Editar ${selected.name}` : "Crear rol"}</h2>
      {selected?.system_managed ? <div className="iam-notice">Este rol técnico es administrado por el sistema.</div> : <form className="iam-form" onSubmit={save}>
        <label>Nombre<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required minLength={2} /></label>
        <label>Descripción<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <div><strong>Permisos del rol</strong><p className="iam-muted">Los permisos solo se asignan a roles. Los usuarios obtienen esos roles directamente o mediante sus grupos.</p></div>
        <CheckList items={permissions.filter((item) => item.active)} selected={form.permission_codes} getValue={(item) => item.code} onToggle={togglePermission} render={(item) => <PermissionLabel permission={item} />} />
        <button className={`iam-button primary iam-persist-action ${canPersistRole ? "pending" : ""}`} disabled={!canPersistRole}>{selected ? "Guardar cambios" : "Crear rol"}</button>
      </form>}
    </section>
  </div>;
}

function GroupsPanel({ groups, roles, users, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [draftRoleIds, setDraftRoleIds] = useState([]);
  const [draftMemberIds, setDraftMemberIds] = useState([]);
  const [savingAssignments, setSavingAssignments] = useState(false);
  const selected = groups.find((item) => item.id === selectedId) || null;
  const groupDirty = useMemo(() => Boolean(selected) && (!sameIds(draftRoleIds, selected.role_ids) || !sameIds(draftMemberIds, selected.member_ids)), [draftRoleIds, draftMemberIds, selected]);

  useEffect(() => {
    setDraftRoleIds([...(selected?.role_ids || [])]);
    setDraftMemberIds([...(selected?.member_ids || [])]);
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
    try {
      await iamApi(`/api/iam/groups/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleDraftRole = (roleId, checked) => setDraftRoleIds((current) => checked ? [...new Set([...current, roleId])] : current.filter((item) => item !== roleId));
  const toggleDraftMember = (userId, checked) => setDraftMemberIds((current) => checked ? [...new Set([...current, userId])] : current.filter((item) => item !== userId));

  const saveGroupAssignments = async () => {
    if (!selected || !groupDirty || savingAssignments) return;
    setSavingAssignments(true);
    setError("");
    try {
      await iamApi(`/api/iam/groups/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role_ids: draftRoleIds, member_ids: draftMemberIds }),
      });
      await reload();
    } catch (error) { setError(error.message); }
    finally { setSavingAssignments(false); }
  };

  return <div className="iam-grid">
    <section className="iam-card">
      <h2>Grupos</h2>
      <form className="iam-form" onSubmit={createGroup}>
        <label>Nuevo grupo<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ej. Junta Directiva, Finanzas, Procurement" required /></label>
        <label>Descripción<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <button className="iam-button primary">Crear grupo</button>
      </form>
      <div className="iam-section iam-list">{groups.map((group) => <button key={group.id} className={`iam-list-item ${selectedId === group.id ? "selected" : ""}`} onClick={() => selectGroup(group.id)}><span className="iam-list-main"><strong>{group.name}</strong><small>{group.member_ids.length} usuario(s) · {group.role_ids.length} rol(es)</small></span><span>{group.active ? "Activo" : "Inactivo"}</span></button>)}</div>
    </section>
    <section className="iam-card">{!selected ? <p className="iam-empty">Selecciona un grupo para administrar sus roles y miembros.</p> : <>
      <span hidden data-unsaved={groupDirty ? "true" : "false"} />
      <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.description || "Sin descripción"}</p></div><button className="iam-button" onClick={() => patchGroup({ active: !selected.active })}>{selected.active ? "Inactivar" : "Activar"}</button></div>
      <div className="iam-toolbar"><button className="iam-button" onClick={() => { const value = window.prompt("Nuevo nombre del grupo", selected.name); if (value?.trim()) patchGroup({ name: value.trim() }); }}>Renombrar</button><button className={`iam-button primary iam-persist-action ${groupDirty ? "pending" : ""}`} disabled={!groupDirty || savingAssignments} onClick={saveGroupAssignments}>{savingAssignments ? "Guardando..." : "Guardar cambios"}</button></div>
      <div className="iam-section"><h3>Roles del grupo</h3><p className="iam-muted">Los miembros heredan los permisos definidos por estos roles.</p><CheckList items={roles.filter((item) => item.active && !item.system_managed)} selected={draftRoleIds} onToggle={toggleDraftRole} render={(role) => <><strong>{role.name}</strong><small>{role.permission_codes.join(" · ") || "Sin permisos"}</small></>} /></div>
      <div className="iam-section"><h3>Miembros</h3><CheckList items={users.filter((item) => !item.is_system_account)} selected={draftMemberIds} onToggle={toggleDraftMember} render={(user) => <><strong>{user.name}</strong><small>{user.email}</small></>} /></div>
    </>}</section>
  </div>;
}

function UsersPanel({ users, groups, roles, permissions, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyUser);
  const [draftGroupIds, setDraftGroupIds] = useState([]);
  const [draftRoleIds, setDraftRoleIds] = useState([]);
  const [savingAccess, setSavingAccess] = useState(false);
  const selected = users.find((item) => item.id === selectedId) || null;
  const userDirty = useMemo(() => Boolean(selected) && !selected.is_system_account && (!sameIds(draftGroupIds, selected.group_ids) || !sameIds(draftRoleIds, selected.role_ids)), [draftGroupIds, draftRoleIds, selected]);

  useEffect(() => {
    setDraftGroupIds([...(selected?.group_ids || [])]);
    setDraftRoleIds([...(selected?.role_ids || [])]);
  }, [selectedId, selected?.id, JSON.stringify(selected?.group_ids || []), JSON.stringify(selected?.role_ids || [])]);

  const selectUser = (userId) => {
    if (userDirty && !window.confirm("Hay cambios sin guardar para este usuario. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(userId);
    setCreating(false);
  };

  const startCreate = () => {
    if (userDirty && !window.confirm("Hay cambios sin guardar para este usuario. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(null);
    setCreating(true);
    setForm(emptyUser);
  };

  const createUser = async (event) => {
    event.preventDefault();
    try {
      await iamApi("/api/iam/users", { method: "POST", body: JSON.stringify(form) });
      setCreating(false); setForm(emptyUser); await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleActive = async () => {
    if (userDirty && !window.confirm("Hay cambios de acceso sin guardar. ¿Deseas descartarlos y cambiar el estado del usuario?")) return;
    try {
      await iamApi(`/api/iam/users/${selected.id}`, { method: "PATCH", body: JSON.stringify({ active: !selected.active }) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleDraftGroup = (value, checked) => setDraftGroupIds((current) => checked ? [...new Set([...current, value])] : current.filter((item) => item !== value));
  const toggleDraftRole = (value, checked) => setDraftRoleIds((current) => checked ? [...new Set([...current, value])] : current.filter((item) => item !== value));

  const saveAccess = async () => {
    if (!selected || !userDirty || savingAccess) return;
    setSavingAccess(true);
    setError("");
    try {
      await iamApi(`/api/iam/users/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ group_ids: draftGroupIds, role_ids: draftRoleIds }),
      });
      await reload();
    } catch (error) { setError(error.message); }
    finally { setSavingAccess(false); }
  };

  return <div className="iam-grid">
    <section className="iam-card">
      <div className="iam-toolbar"><h2>Usuarios</h2><button className="iam-button" onClick={startCreate}>+ Usuario</button></div>
      <div className="iam-list">{users.map((user) => <button key={user.id} className={`iam-list-item ${selectedId === user.id ? "selected" : ""}`} onClick={() => selectUser(user.id)}><span className="iam-list-main"><strong>{user.name}</strong><small>{user.email}</small></span>{user.is_system_account ? <span className="iam-system">SISTEMA</span> : <span>{user.active ? "Activo" : "Inactivo"}</span>}</button>)}</div>
    </section>
    <section className="iam-card">{creating ? <form className="iam-form" onSubmit={createUser}>
      <h2>Crear usuario</h2>
      <div className="iam-two-col"><label>Nombre<input required value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label><label>Apellido<input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label></div>
      <div className="iam-two-col"><label>Segundo nombre<input value={form.middle_name} onChange={(event) => setForm({ ...form, middle_name: event.target.value })} /></label><label>Segundo apellido<input value={form.second_last_name} onChange={(event) => setForm({ ...form, second_last_name: event.target.value })} /></label></div>
      <label>Identificación<input required value={form.identity_document} onChange={(event) => setForm({ ...form, identity_document: event.target.value })} /></label>
      <label>Correo<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label>Teléfono<input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
      <button className="iam-button primary">Crear e invitar</button>
    </form> : !selected ? <p className="iam-empty">Selecciona un usuario o crea uno nuevo.</p> : <>
      <span hidden data-unsaved={userDirty ? "true" : "false"} />
      <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.email}</p></div>{selected.is_system_account ? <span className="iam-system">CUENTA TÉCNICA PROTEGIDA</span> : <button className="iam-button" onClick={toggleActive}>{selected.active ? "Inactivar" : "Activar"}</button>}</div>
      {selected.is_system_account ? <div className="iam-notice">Esta cuenta está separada del flujo financiero y se administra mediante la política técnica del sistema.</div> : <>
        <div className="iam-section"><h3>Grupos</h3><p className="iam-muted">Los grupos otorgan a sus miembros los roles configurados en el grupo.</p><CheckList items={groups.filter((item) => item.active)} selected={draftGroupIds} onToggle={toggleDraftGroup} render={(item) => <><strong>{item.name}</strong><small>{item.description || "Grupo de usuarios"}</small></>} /></div>
        <div className="iam-section"><h3>Roles directos</h3><p className="iam-muted">Asigna un rol directamente solo cuando no corresponda heredarlo mediante un grupo.</p><CheckList items={roles.filter((item) => item.active && !item.system_managed)} selected={draftRoleIds} onToggle={toggleDraftRole} render={(item) => <><strong>{item.name}</strong><small>{item.permission_codes.join(" · ") || "Sin permisos"}</small></>} /></div>
        <div className="iam-toolbar"><span className="iam-muted">Los cambios no se aplican hasta guardar.</span><button className={`iam-button primary iam-persist-action ${userDirty ? "pending" : ""}`} disabled={!userDirty || savingAccess} onClick={saveAccess}>{savingAccess ? "Guardando..." : "Guardar cambios"}</button></div>
      </>}
      <div className="iam-section"><h3>Permisos efectivos</h3>{userDirty && <p className="iam-muted">Este resumen se actualizará después de guardar los cambios.</p>}{selected.effective_permission_codes.length ? selected.effective_permission_codes.map((code) => <div className="iam-permission-row" key={code}><strong>{permissions.find((item) => item.code === code)?.name || code}</strong><code>{code}</code><small>{(selected.permission_sources?.[code] || []).join(" · ")}</small></div>) : <p className="iam-empty">Este usuario no tiene permisos efectivos.</p>}</div>
    </>}</section>
  </div>;
}

function PermissionsPanel({ permissions }) {
  return <section className="iam-card"><h2>Permisos del producto</h2><p className="iam-muted">Los permisos son capacidades atómicas del producto y solo se asignan a roles. Los usuarios reciben roles directamente o a través de grupos.</p><div className="iam-list">{permissions.map((permission) => <div className="iam-list-item" key={permission.code}><span className="iam-list-main"><strong>{permission.name}</strong><small>{permission.code}</small><small>{permission.description}</small></span><span>{permission.active ? "Activo" : "Inactivo"}</span></div>)}</div></section>;
}

function IamConsole() {
  const [tab, setTab] = useState("users");
  const [data, setData] = useState({ permissions: [], roles: [], groups: [], users: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = async () => {
    setError("");
    const me = await iamApi("/api/iam/me/permissions");
    if (!me.permission_codes.includes("config:manage")) throw new Error("No tienes permiso para administrar la configuración de accesos");
    const [permissions, roles, groups, users] = await Promise.all([
      iamApi("/api/iam/permissions"),
      iamApi("/api/iam/roles"),
      iamApi("/api/iam/groups"),
      iamApi("/api/iam/users"),
    ]);
    setData({ permissions, roles, groups, users });
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
      window.setTimeout(() => { if (window.location.hash === "#access-management") window.location.hash = ""; }, 0);
    };
    topbar.addEventListener("click", handleTopbarClick);
    return () => topbar.removeEventListener("click", handleTopbarClick);
  }, []);

  if (loading) return <div className="iam-overlay"><main className="iam-shell"><div className="iam-loading">Cargando configuración de accesos…</div></main></div>;
  const tabs = [["users", "Usuarios"], ["groups", "Grupos"], ["roles", "Roles"], ["permissions", "Permisos"]];
  return <div className="iam-overlay"><main className="iam-shell">
    <header className="iam-header"><p className="iam-eyebrow">CONFIGURACIÓN · ACCESOS</p><h1>Usuarios, grupos, roles y permisos</h1><p className="iam-muted">Modelo de acceso: Usuario → Grupo/Rol → Permisos. Los cargos pertenecen al organigrama y no otorgan acceso.</p></header>
    {error && <div className="iam-notice error">{error}</div>}
    <div className="iam-page-nav"><nav className="iam-tabs">{tabs.map(([value, label]) => <button className={tab === value ? "active" : ""} key={value} onClick={() => setTab(value)}>{label}</button>)}</nav><button className="iam-button iam-refresh" onClick={() => reload().catch((e) => setError(e.message))}>↻ Recargar</button></div>
    {tab === "users" && <UsersPanel {...data} reload={reload} setError={setError} />}
    {tab === "groups" && <GroupsPanel {...data} reload={reload} setError={setError} />}
    {tab === "roles" && <RolesPanel {...data} reload={reload} setError={setError} />}
    {tab === "permissions" && <PermissionsPanel permissions={data.permissions} />}
  </main></div>;
}

let mounted = false;
let root = null;
function renderForHash() {
  const active = window.location.hash === "#access-management";
  if (active && !mounted) {
    const host = document.createElement("div");
    host.id = "iam-admin-root";
    document.body.appendChild(host);
    root = createRoot(host);
    root.render(<IamConsole />);
    mounted = true;
  } else if (!active && mounted) {
    root?.unmount();
    document.getElementById("iam-admin-root")?.remove();
    root = null;
    mounted = false;
  }
}

const legacyAccessMenuLabels = new Set(["Personas", "Usuarios", "Organigrama"]);
function injectAccessMenu() {
  document.querySelectorAll(".config-menu-items").forEach((menu) => {
    menu.querySelectorAll("button").forEach((button) => {
      if (legacyAccessMenuLabels.has(button.textContent?.trim())) button.remove();
    });
    if (menu.querySelector('[data-iam-access="true"]')) return;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.iamAccess = "true";
    button.textContent = "Accesos";
    button.addEventListener("click", () => { window.location.hash = "access-management"; });
    menu.appendChild(button);
  });
}

window.addEventListener("hashchange", renderForHash);
new MutationObserver(injectAccessMenu).observe(document.documentElement, { childList: true, subtree: true });
document.addEventListener("DOMContentLoaded", () => { injectAccessMenu(); renderForHash(); });
