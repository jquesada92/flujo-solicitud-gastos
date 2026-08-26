import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./iam-admin.css";
import "./iam-inheritance.css";
import "./iam-responsive.css";

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
  role_ids: [],
};

const normalizeIds = (values) => [...(values || [])].map(Number).sort((a, b) => a - b);
const sameIds = (left, right) => JSON.stringify(normalizeIds(left)) === JSON.stringify(normalizeIds(right));
const normalizeCodes = (values) => [...new Set(values || [])].sort();
const sameCodes = (left, right) => JSON.stringify(normalizeCodes(left)) === JSON.stringify(normalizeCodes(right));
const SYSTEM_ONLY_PERMISSION_CODES = new Set(["config:manage"]);

function CheckList({ items, selected, onToggle, getValue = (item) => item.id, render, disabled = false, isItemDisabled = () => false }) {
  const values = new Set(selected || []);
  return (
    <div className="iam-checks">
      {items.map((item) => {
        const value = getValue(item);
        const itemDisabled = disabled || isItemDisabled(item);
        return (
          <label className="iam-check" key={String(value)}>
            <input
              type="checkbox"
              checked={values.has(value)}
              disabled={itemDisabled}
              onChange={() => !itemDisabled && onToggle(value, !values.has(value))}
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

function RolesPanel({ permissions, roles, groups, onRoleSaved, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [recovery, setRecovery] = useState(null);
  const [form, setForm] = useState({ name: "", description: "", permission_codes: [], limit_users: false, max_users: "" });
  const selected = roles.find((item) => item.id === selectedId) || null;
  const selectedGroup = selected
    ? groups.find((group) => (group.role_ids || []).includes(selected.id)) || null
    : null;
  const inheritedPermissionCodes = selectedGroup?.active ? selectedGroup.permission_codes || [] : [];
  const configuredPermissionCodes = normalizeCodes([
    ...form.permission_codes,
    ...inheritedPermissionCodes,
  ]);
  const roleCanGrantAccess = !selectedGroup || selectedGroup.active;
  const contributedPermissionCodes = roleCanGrantAccess
    ? configuredPermissionCodes.filter((code) => !SYSTEM_ONLY_PERMISSION_CODES.has(code))
    : [];
  const reservedPermissionCodes = configuredPermissionCodes.filter((code) => SYSTEM_ONLY_PERMISSION_CODES.has(code));
  const displayRoleName = (role) => (
    selectedId === role.id && form.name.trim() ? form.name.trim() : role.name
  );
  const roleDirty = useMemo(() => {
    if (!selected) return Boolean(form.name.trim() || form.description.trim() || form.permission_codes.length || form.limit_users);
    return (
      form.name !== selected.name
      || form.description !== (selected.description || "")
      || !sameCodes(form.permission_codes, selected.permission_codes)
      || form.limit_users !== (selected.max_users !== null)
      || (form.limit_users && Number(form.max_users) !== selected.max_users)
    );
  }, [form, selected]);
  const roleBeingEdited = selected || recovery;
  const minimumRoleLimit = Math.max(1, roleBeingEdited?.assigned_user_count || 0);
  const roleLimitIsValid = !form.limit_users || (
    Number.isInteger(Number(form.max_users))
    && Number(form.max_users) >= minimumRoleLimit
  );
  const canPersistRole = roleDirty && form.name.trim().length >= 2 && roleLimitIsValid;

  const confirmDiscardRoleDraft = (message) => (
    !roleDirty || window.confirm(message)
  );

  const selectRole = (roleId) => {
    if (roleId === selectedId) return;
    if (!confirmDiscardRoleDraft("Hay cambios sin guardar en este rol. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(roleId);
    setRecovery(null);
  };

  const startNewRole = () => {
    if (!confirmDiscardRoleDraft("Hay cambios sin guardar en este rol. ¿Deseas descartarlos y crear otro rol?")) return;
    setSelectedId(null);
    setRecovery(null);
    setForm({ name: "", description: "", permission_codes: [], limit_users: false, max_users: "" });
  };

  useEffect(() => {
    setForm(selected ? {
      name: selected.name,
      description: selected.description || "",
      permission_codes: selected.permission_codes || [],
      limit_users: selected.max_users !== null,
      max_users: selected.max_users ?? "",
    } : { name: "", description: "", permission_codes: [], limit_users: false, max_users: "" });
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
      const target = selected || recovery;
      const saved = await iamApi(target ? `/api/iam/roles/${target.id}` : "/api/iam/roles", {
        method: target ? "PATCH" : "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description,
          permission_codes: form.permission_codes,
          max_users: form.limit_users ? Number(form.max_users) : null,
          active: true,
        }),
      });
      setRecovery(null);
      onRoleSaved(saved);
      setSelectedId(saved.id);
    } catch (error) { setError(error.message); }
  };

  const findRecovery = async () => {
    if (selected || form.name.trim().length < 2) return;
    try {
      const candidate = await iamApi(`/api/iam/roles/recovery?name=${encodeURIComponent(form.name.trim())}`);
      if (candidate && window.confirm(`El rol “${candidate.name}” ya existe inactivo. ¿Deseas recuperar sus datos y reactivarlo al guardar?`)) {
        setRecovery(candidate);
        setForm({
          name: candidate.name,
          description: candidate.description || "",
          permission_codes: candidate.permission_codes || [],
          limit_users: candidate.max_users !== null,
          max_users: candidate.max_users ?? "",
        });
      }
    } catch (error) { setError(error.message); }
  };

  const toggleActive = async (role) => {
    if (!confirmDiscardRoleDraft("Hay cambios sin guardar en este rol. ¿Deseas descartarlos y cambiar el estado?")) return;
    try {
      const saved = await iamApi(`/api/iam/roles/${role.id}`, { method: "PATCH", body: JSON.stringify({ active: !role.active }) });
      onRoleSaved(saved);
      if (role.id === selectedId) {
        setSelectedId(null);
        setRecovery(null);
      }
    } catch (error) { setError(error.message); }
  };

  return <div className="iam-grid iam-roles-grid">
    <span hidden data-unsaved={roleDirty ? "true" : "false"} />
    <section className="iam-card iam-role-list-card">
      <div className="iam-toolbar"><h2>Roles</h2><button className="iam-button" onClick={startNewRole}>+ Nuevo</button></div>
      <div className="iam-list iam-role-list">{roles.filter((role) => role.active).map((role) => <div className={`iam-list-item iam-role-list-item ${selectedId === role.id ? "selected" : ""}`} key={role.id}>
        <button className="iam-button iam-role-select" onClick={() => selectRole(role.id)}><span className="iam-list-main"><strong>{displayRoleName(role)}</strong><small>{role.permission_codes.join(" · ") || "Sin permisos"}</small><small className="iam-role-capacity">{role.assigned_user_count} usuario(s) activo(s) · {role.max_users === null ? "Sin límite" : `Máximo ${role.max_users}`}</small></span></button>
        {role.system_managed ? <span className="iam-system iam-role-status">SISTEMA</span> : <button className="iam-button iam-role-status" onClick={() => toggleActive(role)}>{role.active ? "Activo" : "Inactivo"}</button>}
      </div>)}</div>
    </section>
    <section className="iam-card">
      <h2>{selected ? `Editar ${form.name.trim() || selected.name}` : recovery ? `Reactivar ${recovery.name}` : "Crear rol"}</h2>
      {selected?.system_managed ? <div className="iam-notice">Este rol técnico global es administrado por el sistema.</div> : <form className="iam-form" onSubmit={save}>
        <label>Nombre<input value={form.name} onChange={(event) => { setRecovery(null); setForm({ ...form, name: event.target.value }); }} onBlur={findRecovery} required minLength={2} /></label>
        <label>Descripción<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <fieldset className="iam-role-limit">
          <label className="iam-role-limit-toggle"><input type="checkbox" checked={form.limit_users} onChange={(event) => setForm((current) => ({ ...current, limit_users: event.target.checked, max_users: event.target.checked ? (current.max_users || String(minimumRoleLimit)) : "" }))} /><span>Limitar cantidad de usuarios activos</span></label>
          <label>Máximo de usuarios activos<input type="number" inputMode="numeric" min={minimumRoleLimit} step="1" value={form.max_users} disabled={!form.limit_users} onChange={(event) => setForm((current) => ({ ...current, max_users: event.target.value }))} /></label>
          <small>{roleBeingEdited ? `Actualmente hay ${roleBeingEdited.assigned_user_count} usuario(s) activo(s) asignado(s).` : "Los usuarios inactivos conservan el rol, pero no consumen cupo."}</small>
          {form.limit_users && !roleLimitIsValid && <small className="iam-field-error">Indica un número entero igual o mayor que {minimumRoleLimit}.</small>}
        </fieldset>
        <div><strong>Permisos propios del rol</strong><p className="iam-muted">Estos permisos se conservan en el rol. {selectedGroup?.active ? `Además hereda los permisos de ${selectedGroup.name}.` : selectedGroup ? `Está vinculado a ${selectedGroup.name}, pero el grupo está inactivo y actualmente no aporta permisos.` : "Si luego se vincula a un grupo, sumará también los permisos de ese grupo."}</p></div>
        <CheckList
          items={permissions.filter((item) => item.active)}
          selected={form.permission_codes}
          getValue={(item) => item.code}
          onToggle={togglePermission}
          isItemDisabled={(item) => SYSTEM_ONLY_PERMISSION_CODES.has(item.code)}
          render={(item) => <>
            <PermissionLabel permission={item} />
            {inheritedPermissionCodes.includes(item.code) && <small className="iam-inherited">{form.permission_codes.includes(item.code) ? "También heredado" : "Heredado"} de {selectedGroup.name}</small>}
            {SYSTEM_ONLY_PERMISSION_CODES.has(item.code) && <small>Reservado para cuentas técnicas; no se asigna desde roles.</small>}
          </>}
        />
        {selectedGroup && <div className="iam-effective-summary"><strong>Permisos aportados por este rol</strong><small>{contributedPermissionCodes.join(" · ") || "Sin permisos ordinarios"}</small>{reservedPermissionCodes.length > 0 && <small>Reservado sin efecto para usuarios ordinarios: {reservedPermissionCodes.join(" · ")}</small>}<small>{selectedGroup.active ? "La herencia no se copia al rol; si el rol sale del grupo, conserva solamente sus permisos propios." : "El grupo inactivo no aporta permisos hasta que vuelva a activarse."}</small></div>}
        <button className={`iam-button primary iam-persist-action ${canPersistRole ? "pending" : ""}`} disabled={!canPersistRole}>{selected ? "Guardar cambios" : recovery ? "Reactivar rol" : "Crear rol"}</button>
      </form>}
    </section>
  </div>;
}

function GroupsPanel({ groups, roles, users, permissions, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [draftRoleIds, setDraftRoleIds] = useState([]);
  const [draftPermissionCodes, setDraftPermissionCodes] = useState([]);
  const [draftMemberIds, setDraftMemberIds] = useState([]);
  const [savingAssignments, setSavingAssignments] = useState(false);
  const [recovery, setRecovery] = useState(null);
  const selected = groups.find((item) => item.id === selectedId) || null;
  const groupForRole = (roleId) => groups.find((group) => (group.role_ids || []).includes(roleId)) || null;
  const groupDirty = useMemo(() => Boolean(selected) && (
    !sameIds(draftRoleIds, selected.role_ids)
    || !sameCodes(draftPermissionCodes, selected.permission_codes)
  ), [draftRoleIds, draftPermissionCodes, selected]);
  const newGroupDirty = Boolean(name.trim() || description.trim());

  useEffect(() => {
    setDraftRoleIds([...(selected?.role_ids || [])]);
    setDraftPermissionCodes([...(selected?.permission_codes || [])]);
    setDraftMemberIds([...(selected?.member_ids || [])]);
  }, [selectedId, selected?.id, JSON.stringify(selected?.role_ids || []), JSON.stringify(selected?.permission_codes || []), JSON.stringify(selected?.member_ids || [])]);

  const selectGroup = (groupId) => {
    if (groupDirty && !window.confirm("Hay cambios sin guardar en este grupo. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(groupId);
  };

  const createGroup = async (event) => {
    event.preventDefault();
    if (groupDirty && !window.confirm("Hay cambios sin guardar en este grupo. ¿Deseas descartarlos y crear otro grupo?")) return;
    try {
      const saved = await iamApi(recovery ? `/api/iam/groups/${recovery.id}` : "/api/iam/groups", { method: recovery ? "PATCH" : "POST", body: JSON.stringify({ name, description, active: true }) });
      setName(""); setDescription(""); setRecovery(null); await reload(); setSelectedId(saved.id);
    } catch (error) { setError(error.message); }
  };

  const findRecovery = async () => {
    if (name.trim().length < 2) return;
    try {
      const candidate = await iamApi(`/api/iam/groups/recovery?name=${encodeURIComponent(name.trim())}`);
      if (candidate && window.confirm(`El grupo “${candidate.name}” está inactivo. ¿Deseas recuperar sus datos?`)) {
        setRecovery(candidate);
        setName(candidate.name);
        setDescription(candidate.description || "");
      }
    } catch (error) { setError(error.message); }
  };

  const patchGroup = async (payload) => {
    try {
      await iamApi(`/api/iam/groups/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  const toggleDraftRole = (roleId, checked) => setDraftRoleIds((current) => checked ? [...new Set([...current, roleId])] : current.filter((item) => item !== roleId));
  const toggleDraftPermission = (code, checked) => setDraftPermissionCodes((current) => checked ? [...new Set([...current, code])] : current.filter((item) => item !== code));

  const saveGroupAssignments = async () => {
    if (!selected || !groupDirty || savingAssignments) return;
    setSavingAssignments(true);
    setError("");
    try {
      await iamApi(`/api/iam/groups/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          role_ids: draftRoleIds,
          permission_codes: draftPermissionCodes,
          member_ids: draftMemberIds,
        }),
      });
      await reload();
    } catch (error) { setError(error.message); }
    finally { setSavingAssignments(false); }
  };

  return <div className="iam-grid">
    <span hidden data-unsaved={groupDirty || newGroupDirty ? "true" : "false"} />
    <section className="iam-card">
      <h2>Grupos</h2>
      <form className="iam-form" onSubmit={createGroup}>
        <label>Nuevo grupo<input value={name} onChange={(event) => { setRecovery(null); setName(event.target.value); }} onBlur={findRecovery} placeholder="Ej. Junta Directiva, Solicitudes, Administración" required /></label>
        <label>Descripción<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <button className="iam-button primary">{recovery ? "Reactivar grupo" : "Crear grupo"}</button>
      </form>
      <div className="iam-section iam-list">{groups.filter((group) => group.active).map((group) => <button key={group.id} className={`iam-list-item ${selectedId === group.id ? "selected" : ""}`} onClick={() => selectGroup(group.id)}><span className="iam-list-main"><strong>{group.name}</strong><small>{group.member_ids.length} usuario(s) · {group.role_ids.length} rol(es) · {(group.permission_codes || []).length} permiso(s)</small></span><span>Activo</span></button>)}</div>
    </section>
    <section className="iam-card">{!selected ? <p className="iam-empty">Selecciona un grupo para administrar sus permisos heredados y roles opcionales.</p> : <>
      <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.description || "Sin descripción"}</p></div><button className="iam-button" disabled={groupDirty} title={groupDirty ? "Guarda o descarta los cambios pendientes primero" : ""} onClick={() => patchGroup({ active: !selected.active })}>{selected.active ? "Inactivar" : "Activar"}</button></div>
      <div className="iam-toolbar"><button className="iam-button" disabled={groupDirty} title={groupDirty ? "Guarda o descarta los cambios pendientes primero" : ""} onClick={() => { const value = window.prompt("Nuevo nombre del grupo", selected.name); if (value?.trim()) patchGroup({ name: value.trim() }); }}>Renombrar</button><button className={`iam-button primary iam-persist-action ${groupDirty ? "pending" : ""}`} disabled={!groupDirty || savingAssignments} onClick={saveGroupAssignments}>{savingAssignments ? "Guardando..." : "Guardar cambios"}</button></div>
      <div className="iam-section"><h3>Permisos del grupo</h3><p className="iam-muted">{selected.active ? "Todos los roles vinculados heredan estos permisos. Los permisos propios de cada rol se suman y no se reemplazan." : "La configuración se conserva, pero el grupo inactivo no concede permisos. Volverá a heredarse al activarlo."}</p><CheckList items={permissions.filter((item) => item.active)} selected={draftPermissionCodes} getValue={(item) => item.code} onToggle={toggleDraftPermission} isItemDisabled={(item) => SYSTEM_ONLY_PERMISSION_CODES.has(item.code)} render={(item) => <><PermissionLabel permission={item} />{SYSTEM_ONLY_PERMISSION_CODES.has(item.code) && <small>Reservado para cuentas técnicas; no se asigna desde grupos.</small>}</>} /></div>
      <div className="iam-section"><h3>Roles del grupo</h3><p className="iam-muted">Un grupo puede existir sin roles. Cada rol puede pertenecer como máximo a un grupo; quitarlo de todos los grupos lo convierte en rol global y conserva sus permisos propios.</p><CheckList items={roles.filter((item) => item.active && !item.system_managed)} selected={draftRoleIds} onToggle={toggleDraftRole} isItemDisabled={(role) => { const owner = groupForRole(role.id); return Boolean(owner && owner.id !== selected.id); }} render={(role) => { const owner = groupForRole(role.id); const selectedHere = draftRoleIds.includes(role.id); const inheritedText = draftPermissionCodes.join(" · ") || "ninguno"; return <><strong>{role.name}</strong><small>Propios: {role.permission_codes.join(" · ") || "ninguno"}</small><small>{owner && owner.id !== selected.id ? `Pertenece a ${owner.name}` : selectedHere ? selected.active ? `Heredados de este grupo: ${inheritedText}` : `Configurados en este grupo, sin efecto mientras esté inactivo: ${inheritedText}` : selected.active ? `Al vincularlo heredará: ${inheritedText}` : `Al vincularlo y activar el grupo heredará: ${inheritedText}`}</small></>; }} /></div>
      <div className="iam-section"><h3>Miembros</h3><p className="iam-muted">Solo lectura. La membresía se obtiene al asignar un rol de este grupo desde la ficha del usuario.</p><CheckList items={users.filter((item) => !item.is_system_account && draftMemberIds.includes(item.id))} selected={draftMemberIds} onToggle={() => {}} disabled render={(user) => <><strong>{user.name}</strong><small>{user.email}</small></>} /></div>
    </>}</section>
  </div>;
}

function UsersPanel({ users, groups, roles, permissions, reload, setError }) {
  const [selectedId, setSelectedId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyUser);
  const [draftRoleIds, setDraftRoleIds] = useState([]);
  const [savingAccess, setSavingAccess] = useState(false);
  const [passwordRequestUserId, setPasswordRequestUserId] = useState(null);
  const [passwordNotice, setPasswordNotice] = useState(null);
  const [recovery, setRecovery] = useState(null);
  const [userQuery, setUserQuery] = useState("");
  const selected = users.find((item) => item.id === selectedId) || null;
  const userDirty = useMemo(() => Boolean(selected) && !selected.is_system_account && !sameIds(draftRoleIds, selected.role_ids), [draftRoleIds, selected]);
  const createUserDirty = creating && Boolean(
    form.identity_document.trim()
    || form.first_name.trim()
    || form.middle_name.trim()
    || form.last_name.trim()
    || form.second_last_name.trim()
    || form.email.trim()
    || form.phone.trim()
    || form.role_ids.length
  );
  const pendingUserChanges = userDirty || createUserDirty;
  const assignableRoles = useMemo(() => roles.filter((role) => role.active && !role.system_managed), [roles]);
  const selectedRoleId = draftRoleIds[0] || "";
  const selectedRole = assignableRoles.find((role) => role.id === Number(selectedRoleId)) || null;
  const selectedRoleGroup = selectedRole
    ? groups.find((group) => (group.role_ids || []).includes(selectedRole.id)) || null
    : null;
  const visibleUsers = useMemo(() => {
    const normalizeSearch = (value) => String(value || "")
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLocaleLowerCase("es")
      .trim();
    const query = normalizeSearch(userQuery);
    return users
      .filter((user) => user.active)
      .filter((user) => {
        if (!query) return true;
        const assignedRoles = roles.filter((role) => (user.role_ids || []).includes(role.id));
        const assignedGroups = groups.filter((group) => assignedRoles.some((role) => (group.role_ids || []).includes(role.id)));
        return [
          user.identity_document,
          user.name,
          user.first_name,
          user.middle_name,
          user.last_name,
          user.second_last_name,
          user.email,
          ...assignedRoles.flatMap((role) => [role.name, role.code]),
          ...assignedGroups.flatMap((group) => [group.name, group.code]),
        ].some((value) => normalizeSearch(value).includes(query));
      })
      .slice(0, 10);
  }, [users, roles, groups, userQuery]);

  useEffect(() => {
    setDraftRoleIds(selected?.role_ids?.length ? [selected.role_ids[0]] : []);
  }, [selectedId, selected?.id, JSON.stringify(selected?.role_ids || [])]);

  const selectUser = (userId) => {
    if (pendingUserChanges && !window.confirm("Hay cambios sin guardar para este usuario. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(userId);
    setCreating(false);
  };

  const startCreate = () => {
    if (pendingUserChanges && !window.confirm("Hay cambios sin guardar para este usuario. ¿Deseas descartarlos y continuar?")) return;
    setSelectedId(null);
    setCreating(true);
    setForm(emptyUser);
    setRecovery(null);
  };

  const createUser = async (event) => {
    event.preventDefault();
    try {
      await iamApi(recovery ? `/api/iam/users/${recovery.id}` : "/api/iam/users", { method: recovery ? "PATCH" : "POST", body: JSON.stringify({ ...form, active: true }) });
      setCreating(false); setForm(emptyUser); setRecovery(null); await reload();
    } catch (error) { setError(error.message); }
  };

  const findRecovery = async () => {
    const document = form.identity_document.trim();
    if (document.length < 3) return;
    try {
      const candidate = await iamApi(`/api/iam/users/recovery?identity_document=${encodeURIComponent(document)}`);
      if (candidate && window.confirm(`La identificación ${candidate.identity_document} pertenece a un usuario inactivo. ¿Deseas recuperar sus datos?`)) {
        setRecovery(candidate);
        setForm({
          identity_document: candidate.identity_document || "",
          first_name: candidate.first_name || "",
          middle_name: candidate.middle_name || "",
          last_name: candidate.last_name || "",
          second_last_name: candidate.second_last_name || "",
          email: candidate.email || "",
          phone: candidate.phone || "",
          active: true,
          role_ids: candidate.role_ids?.length ? [candidate.role_ids[0]] : [],
        });
      }
    } catch (error) { setError(error.message); }
  };

  const toggleActive = async () => {
    if (userDirty && !window.confirm("Hay cambios de acceso sin guardar. ¿Deseas descartarlos y cambiar el estado del usuario?")) return;
    try {
      await iamApi(`/api/iam/users/${selected.id}`, { method: "PATCH", body: JSON.stringify({ active: !selected.active }) });
      await reload();
    } catch (error) { setError(error.message); }
  };

  const setRole = (rawRoleId) => {
    const nextRoleId = Number(rawRoleId) || null;
    setDraftRoleIds(nextRoleId ? [nextRoleId] : []);
  };

  const saveAccess = async () => {
    if (!selected || !userDirty || savingAccess) return;
    setSavingAccess(true);
    setError("");
    try {
      await iamApi(`/api/iam/users/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role_ids: draftRoleIds }),
      });
      await reload();
    } catch (error) { setError(error.message); }
    finally { setSavingAccess(false); }
  };

  const regeneratePassword = async (user) => {
    if (!user?.active || user.is_system_account || passwordRequestUserId !== null) return;
    if (!window.confirm(`¿Enviar un enlace de un solo uso para restablecer la contraseña de ${user.name} a ${user.email}? La contraseña actual seguirá vigente hasta que el usuario complete el cambio.`)) return;
    setPasswordRequestUserId(user.id);
    setPasswordNotice(null);
    setError("");
    try {
      await iamApi(`/api/users/${user.id}/regenerate-password`, { method: "POST" });
      setPasswordNotice({
        userId: user.id,
        type: "success",
        text: `Se envió un enlace de un solo uso para restablecer la contraseña a ${user.email}.`,
      });
    } catch (error) {
      setPasswordNotice({ userId: user.id, type: "error", text: error.message });
    } finally {
      setPasswordRequestUserId(null);
    }
  };

  const protectedGlobalRoles = selected
    ? roles.filter((role) => role.system_managed && (selected.role_ids || []).includes(role.id))
    : [];

  return <div className="iam-grid">
    <span hidden data-unsaved={pendingUserChanges ? "true" : "false"} />
    <section className="iam-card">
      <div className="iam-toolbar"><h2>Usuarios</h2><button className="iam-button" onClick={startCreate}>+ Usuario</button></div>
      <label className="iam-form">Buscar usuario<input type="search" value={userQuery} onChange={(event) => setUserQuery(event.target.value)} placeholder="Cédula, nombre, apellido, rol o grupo" /></label>
      <p className="iam-muted">Mostrando {visibleUsers.length} usuario(s), máximo 10.</p>
      <div className="iam-list iam-user-list">{visibleUsers.map((user) => {
        const assignedRoleNames = roles
          .filter((role) => (user.role_ids || []).includes(role.id))
          .map((role) => `${role.name}${role.active ? "" : " (inactivo)"}`);
        return <button key={user.id} className={`iam-list-item ${selectedId === user.id ? "selected" : ""}`} onClick={() => selectUser(user.id)}>
          <span className="iam-list-main">
            <strong>{user.name}</strong>
            <small>{user.email}</small>
            {assignedRoleNames.length > 0 && <small className="iam-user-roles"><strong>{assignedRoleNames.length === 1 ? "Rol" : "Roles"}:</strong> {assignedRoleNames.join(" · ")}</small>}
          </span>
          {user.is_system_account ? <span className="iam-system">SISTEMA</span> : <span>Activo</span>}
        </button>;
      })}</div>
      {!visibleUsers.length && <p className="iam-empty">No hay usuarios activos que coincidan con la búsqueda.</p>}
    </section>
    <section className="iam-card">{creating ? <form className="iam-form" onSubmit={createUser}>
      <h2>{recovery ? "Reactivar usuario" : "Crear usuario"}</h2>
      <div className="iam-two-col"><label>Nombre<input required value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label><label>Segundo nombre<input value={form.middle_name} onChange={(event) => setForm({ ...form, middle_name: event.target.value })} /></label></div>
      <div className="iam-two-col"><label>Apellido<input required value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label><label>Segundo apellido<input value={form.second_last_name} onChange={(event) => setForm({ ...form, second_last_name: event.target.value })} /></label></div>
      <label>Identificación<input required value={form.identity_document} onChange={(event) => { setRecovery(null); setForm({ ...form, identity_document: event.target.value }); }} onBlur={findRecovery} /></label>
      <label>Correo<input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
      <label>Teléfono<input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
      <button className="iam-button primary">{recovery ? "Reactivar usuario" : "Crear e invitar"}</button>
    </form> : !selected ? <p className="iam-empty">Selecciona un usuario o crea uno nuevo.</p> : <>
      <div className="iam-toolbar"><div><h2>{selected.name}</h2><p className="iam-muted">{selected.email}</p></div>{selected.is_system_account ? <span className="iam-system">CUENTA TÉCNICA PROTEGIDA</span> : <button className="iam-button" onClick={toggleActive}>{selected.active ? "Inactivar" : "Activar"}</button>}</div>
      {selected.is_system_account ? <div className="iam-notice">Esta cuenta usa política técnica protegida. Rol global: {protectedGlobalRoles.map((role) => role.name).join(", ") || "Administrador del sistema"}. No se edita desde esta consola.</div> : <>
        <div className="iam-section iam-security-section">
          <div className="iam-toolbar">
            <div><h3>Seguridad</h3><p className="iam-muted">Envía un enlace de un solo uso para crear una contraseña nueva. La contraseña actual seguirá vigente hasta completar el cambio. Esta acción es inmediata y no guarda ni descarta cambios del rol.</p></div>
            <button
              type="button"
              className="iam-button iam-security-action"
              disabled={!selected.active || passwordRequestUserId !== null}
              title={!selected.active ? "Activa el usuario antes de regenerar su contraseña" : ""}
              aria-label={`Regenerar contraseña de ${selected.name}`}
              aria-busy={passwordRequestUserId === selected.id}
              onClick={() => regeneratePassword(selected)}
            >
              {passwordRequestUserId === selected.id ? "Enviando..." : "Regenerar contraseña"}
            </button>
          </div>
          {passwordNotice?.userId === selected.id && <div className={`iam-notice iam-security-notice ${passwordNotice.type}`} role={passwordNotice.type === "error" ? "alert" : "status"} aria-live={passwordNotice.type === "error" ? "assertive" : "polite"}>{passwordNotice.text}</div>}
        </div>
        <div className="iam-section"><h3>Rol</h3><p className="iam-muted">Asigna un único rol al usuario. Si el rol pertenece a un grupo, la membresía se deriva automáticamente y el grupo se muestra solo como información.</p>
          <div className="iam-two-col iam-form">
            <label>Rol asignado<select value={selectedRoleId} onChange={(event) => setRole(event.target.value)}><option value="">Sin rol / sin acceso</option>{assignableRoles.map((role) => { const roleGroup = groups.find((group) => (group.role_ids || []).includes(role.id)) || null; const alreadyAssigned = (selected.role_ids || []).includes(role.id); const roleIsFull = role.max_users !== null && role.assigned_user_count >= role.max_users && !alreadyAssigned; return <option value={role.id} key={role.id} disabled={Boolean((roleGroup && !roleGroup.active) || roleIsFull)}>{role.name}{roleGroup && !roleGroup.active ? " (grupo inactivo)" : roleIsFull ? " (sin cupo)" : role.max_users !== null ? ` (${role.assigned_user_count}/${role.max_users})` : ""}</option>; })}</select></label>
            <label>Grupo<div className="iam-system">{selectedRoleGroup?.active ? `Miembro — ${selectedRoleGroup.name}` : selectedRoleGroup ? `${selectedRoleGroup.name} — Grupo inactivo, sin acceso` : selectedRole ? "Sin grupo — Rol global" : "Sin rol asignado"}</div></label>
          </div>
        </div>
        <div className="iam-toolbar"><span className="iam-muted">Los cambios no se aplican hasta guardar.</span><button className={`iam-button primary iam-persist-action ${userDirty ? "pending" : ""}`} disabled={!userDirty || savingAccess} onClick={saveAccess}>{savingAccess ? "Guardando..." : "Guardar cambios"}</button></div>
      </>}
      <div className="iam-section"><h3>Permisos efectivos</h3>{userDirty && <p className="iam-muted">Este resumen se actualizará después de guardar los cambios.</p>}{selected.effective_permission_codes.length ? selected.effective_permission_codes.map((code) => <div className="iam-permission-row" key={code}><strong>{permissions.find((item) => item.code === code)?.name || code}</strong><code>Permiso: {code}</code><small>Origen: {(selected.permission_sources?.[code] || []).join(" · ")}</small></div>) : <p className="iam-empty">Este usuario no tiene permisos efectivos.</p>}</div>
    </>}</section>
  </div>;
}

function PermissionsPanel({ permissions }) {
  return <section className="iam-card iam-permissions-card"><h2>Permisos del producto</h2><p className="iam-muted">Los permisos son capacidades atómicas del producto. Se asignan como base a grupos o como permisos propios de roles; el usuario recibe la unión mediante su rol asignado.</p><div className="iam-list">{permissions.map((permission) => <div className="iam-list-item" key={permission.code}><span className="iam-list-main"><strong>{permission.name}</strong><small>{permission.code}</small><small>{permission.description}</small></span><span>{permission.active ? "Activo" : "Inactivo"}</span></div>)}</div></section>;
}

function IamConsole() {
  const [tab, setTab] = useState("users");
  const [data, setData] = useState({ permissions: [], roles: [], groups: [], users: [] });
  const [panelRevision, setPanelRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const upsertRole = (savedRole) => {
    setData((current) => {
      const exists = current.roles.some((item) => item.id === savedRole.id);
      const roles = exists
        ? current.roles.map((item) => item.id === savedRole.id ? savedRole : item)
        : [...current.roles, savedRole];
      roles.sort((left, right) => left.name.localeCompare(right.name, "es", { sensitivity: "base" }));
      return { ...current, roles };
    });
  };

  const reload = async () => {
    setError("");
    const me = await iamApi("/api/iam/me/permissions");
    if (!me.permission_codes.includes("config:manage")) throw new Error("No tienes permiso para administrar la configuración de accesos");
    const [permissions, roles, groups, users] = await Promise.all([
      iamApi("/api/iam/permissions"),
      iamApi("/api/iam/roles?include_inactive=true"),
      iamApi("/api/iam/groups?include_inactive=true"),
      iamApi("/api/iam/users"),
    ]);
    setData({ permissions, roles, groups, users });
  };

  const confirmDiscardPending = () => (
    !document.querySelector('#iam-admin-root [data-unsaved="true"]')
    || window.confirm("Hay cambios sin guardar. ¿Deseas descartarlos y continuar?")
  );

  const selectTab = (value) => {
    if (value !== tab && !confirmDiscardPending()) return;
    setTab(value);
  };

  const manualReload = async () => {
    if (!confirmDiscardPending()) return;
    try {
      await reload();
      setPanelRevision((current) => current + 1);
    } catch (e) { setError(e.message); }
  };

  useEffect(() => { reload().catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  useEffect(() => {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return undefined;
    const handleTopbarClick = (event) => {
      if (window.location.hash !== "#access-management") return;
      const target = event.target instanceof Element ? event.target : null;
      const button = target?.closest("button");
      if (!button || !topbar.contains(button)) return;
      if (button.dataset.iamAccess === "true") return;
      if (button.closest(".config-menu") && !button.closest(".config-menu-items")) return;
      if (!confirmDiscardPending()) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      window.setTimeout(() => { if (window.location.hash === "#access-management") window.location.hash = ""; }, 0);
    };
    topbar.addEventListener("click", handleTopbarClick);
    return () => topbar.removeEventListener("click", handleTopbarClick);
  }, []);

  if (loading) return <div className="iam-overlay"><main className="iam-shell"><div className="iam-loading">Cargando configuración de accesos…</div></main></div>;
  const tabs = [["users", "Usuarios"], ["groups", "Grupos"], ["roles", "Roles"], ["permissions", "Permisos"]];
  return <div className="iam-overlay"><main className="iam-shell">
    <header className="iam-header"><p className="iam-eyebrow">CONFIGURACIÓN · ACCESOS</p><h1>Usuarios, grupos, roles y permisos</h1><p className="iam-muted">Modelo de acceso: cada usuario tiene un único rol. Si el rol pertenece a un grupo, deriva su membresía y hereda los permisos del grupo sin perder los permisos propios del rol.</p></header>
    {error && <div className="iam-notice error">{error}</div>}
    <div className="iam-page-nav"><nav className="iam-tabs" role="tablist" aria-label="Secciones de accesos">{tabs.map(([value, label]) => <button role="tab" aria-selected={tab === value} className={tab === value ? "active" : ""} key={value} onClick={() => selectTab(value)}>{label}</button>)}</nav><button className="iam-button iam-refresh" onClick={manualReload}>↻ Recargar</button></div>
    {tab === "users" && <UsersPanel key={`users-${panelRevision}`} {...data} reload={reload} setError={setError} />}
    {tab === "groups" && <GroupsPanel key={`groups-${panelRevision}`} {...data} reload={reload} setError={setError} />}
    {tab === "roles" && <RolesPanel key={`roles-${panelRevision}`} {...data} onRoleSaved={upsertRole} setError={setError} />}
    {tab === "permissions" && <PermissionsPanel key={`permissions-${panelRevision}`} permissions={data.permissions} />}
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
