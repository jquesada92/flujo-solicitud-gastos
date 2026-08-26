import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./user-tracking.css";

const TRACKING_HASH = "#user-tracking";
const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE_URL}${path}`;

async function loadTracking() {
  const token = localStorage.getItem("access_token");
  const response = await fetch(apiUrl("/api/organization/groups"), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    let detail = "No se pudo cargar el seguimiento de usuarios";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

function TrackingPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [onlyPending, setOnlyPending] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    loadTracking()
      .then((result) => { if (active) setData(result); })
      .catch((reason) => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, [refreshKey]);

  const members = useMemo(() => {
    const byId = new Map();
    for (const group of data?.groups || []) {
      for (const member of group.members || []) byId.set(member.id, member);
    }
    return [...byId.values()];
  }, [data]);

  const normalizedQuery = query.trim().toLowerCase();
  const visibleGroups = useMemo(() => (data?.groups || [])
    .map((group) => {
      const groupMatches = !normalizedQuery
        || group.name.toLowerCase().includes(normalizedQuery)
        || String(group.description || "").toLowerCase().includes(normalizedQuery);
      const visibleMembers = (group.members || []).filter((member) => {
        if (onlyPending && !member.pending_actions) return false;
        if (!normalizedQuery || groupMatches) return true;
        return member.name.toLowerCase().includes(normalizedQuery)
          || (member.roles || []).some((role) => role.toLowerCase().includes(normalizedQuery));
      });
      return { ...group, members: visibleMembers };
    })
    .filter((group) => group.members.length || (!onlyPending && normalizedQuery && group.name.toLowerCase().includes(normalizedQuery))),
  [data, normalizedQuery, onlyPending]);

  const totalPending = members.reduce((total, member) => total + Number(member.pending_actions || 0), 0);
  const usersWithPending = members.filter((member) => Number(member.pending_actions || 0) > 0).length;

  return <div className="user-tracking-overlay">
    <main className="user-tracking-shell">
      <section className="user-tracking-hero">
        <div>
          <p className="eyebrow">SEGUIMIENTO · EQUIPO</p>
          <h1>Seguimiento de usuarios</h1>
          <p className="user-tracking-intro">Consulta la carga pendiente del equipo, la composición de los grupos y los roles efectivos de cada miembro. Esta vista es informativa y no modifica accesos.</p>
        </div>
        <button className="secondary" type="button" onClick={() => setRefreshKey((value) => value + 1)}>↻ Recargar</button>
      </section>

      <section className="user-tracking-kpis" aria-label="Resumen de seguimiento">
        <article><span>Miembros activos</span><strong>{members.length}</strong><small>Usuarios incluidos en grupos activos</small></article>
        <article className={usersWithPending ? "attention" : ""}><span>Usuarios con pendientes</span><strong>{usersWithPending}</strong><small>Personas que requieren atención</small></article>
        <article className={totalPending ? "attention" : ""}><span>Acciones pendientes</span><strong>{totalPending}</strong><small>Carga pendiente total del equipo</small></article>
      </section>

      <section className="card user-tracking-controls">
        <label>
          <span>Buscar</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Usuario, grupo o rol" />
        </label>
        <label className="user-tracking-toggle">
          <input type="checkbox" checked={onlyPending} onChange={(event) => setOnlyPending(event.target.checked)} />
          <span>Solo usuarios con acciones pendientes</span>
        </label>
      </section>

      {error && <section className="card"><div className="notice error">{error}</div></section>}
      {!error && !data && <section className="card"><p className="muted">Cargando seguimiento…</p></section>}
      {data && !visibleGroups.length && <section className="card"><p className="muted">No hay resultados para los filtros seleccionados.</p></section>}

      {visibleGroups.map((group) => {
        const groupPending = group.members.reduce((total, member) => total + Number(member.pending_actions || 0), 0);
        return <section className="card user-tracking-group" key={group.id}>
          <header className="user-tracking-group-header">
            <div>
              <p className="eyebrow">GRUPO</p>
              <h2>{group.name}</h2>
              {group.description && <p>{group.description}</p>}
            </div>
            <div className="user-tracking-group-summary">
              <span>{group.members.length} miembro{group.members.length === 1 ? "" : "s"}</span>
              <strong>{groupPending} pendiente{groupPending === 1 ? "" : "s"}</strong>
            </div>
          </header>

          {group.members.length ? <div className="user-tracking-table">
            <div className="user-tracking-row user-tracking-table-head" aria-hidden="true">
              <span>Usuario</span><span>Roles</span><span>Acciones pendientes</span>
            </div>
            {group.members.map((member) => <div className="user-tracking-row" key={member.id}>
              <div className="user-tracking-person"><strong>{member.name}</strong></div>
              <div className="user-tracking-roles">
                {(member.roles || []).length
                  ? member.roles.map((role) => <span key={role}>{role}</span>)
                  : <span className="empty">Sin rol asignado</span>}
              </div>
              <div className={`user-tracking-pending ${member.pending_actions ? "has-pending" : ""}`}>
                <strong>{member.pending_actions}</strong>
                <small>acción{member.pending_actions === 1 ? "" : "es"}</small>
              </div>
            </div>)}
          </div> : <p className="muted">Este grupo no tiene miembros que coincidan con los filtros.</p>}
        </section>;
      })}
    </main>
  </div>;
}

let mounted = false;
let root = null;

function renderTracking() {
  const active = window.location.hash === TRACKING_HASH;
  const navigationButton = document.querySelector('[data-user-tracking="true"]');
  if (navigationButton) {
    navigationButton.dataset.active = String(active);
    if (active) navigationButton.setAttribute("aria-current", "page");
    else navigationButton.removeAttribute("aria-current");
  }
  if (active && !mounted) {
    const host = document.createElement("div");
    host.id = "user-tracking-root";
    document.body.appendChild(host);
    root = createRoot(host);
    root.render(<TrackingPage />);
    mounted = true;
  } else if (!active && mounted) {
    root?.unmount();
    document.getElementById("user-tracking-root")?.remove();
    root = null;
    mounted = false;
  }
}

function injectTrackingButton() {
  const actions = document.querySelector(".topbar .header-actions");
  if (!actions || actions.querySelector('[data-user-tracking="true"]')) return;

  const button = document.createElement("button");
  button.type = "button";
  button.dataset.userTracking = "true";
  button.textContent = "Seguimiento";
  button.addEventListener("click", () => {
    if (window.location.hash !== TRACKING_HASH) window.location.hash = "user-tracking";
  });

  const requestsButton = [...actions.querySelectorAll("button")]
    .find((item) => item.textContent?.trim() === "Solicitudes");
  if (requestsButton) requestsButton.insertAdjacentElement("afterend", button);
  else actions.prepend(button);
}

function leaveTrackingOnNavigation(event) {
  if (window.location.hash !== TRACKING_HASH) return;
  const target = event.target instanceof Element ? event.target : null;
  const button = target?.closest(".topbar button");
  if (!button || button.dataset.userTracking === "true") return;
  window.location.hash = "";
}

window.addEventListener("hashchange", renderTracking);
document.addEventListener("click", leaveTrackingOnNavigation, true);
new MutationObserver(injectTrackingButton).observe(document.documentElement, { childList: true, subtree: true });
document.addEventListener("DOMContentLoaded", () => {
  injectTrackingButton();
  renderTracking();
});
