import React, { useEffect, useState } from "react";
import "./organization-overview.css";

const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE_URL}${path}`;

async function loadGroups() {
  const token = localStorage.getItem("access_token");
  const response = await fetch(apiUrl("/api/organization/groups"), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    let detail = "No se pudo cargar la información de los grupos";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

export default function OrganizationOverview({ refreshKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    loadGroups()
      .then((result) => { if (active) setData(result); })
      .catch((reason) => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, [refreshKey]);

  return <section className="card organization-overview">
    <div className="card-heading">
      <div><p className="eyebrow">ORGANIZACIÓN</p><h2>Grupos y responsabilidades</h2></div>
    </div>
    <p className="organization-help">Consulta quién pertenece a cada grupo, qué roles tiene y cuántas acciones de flujo tiene pendientes.</p>
    {error && <div className="notice error">{error}</div>}
    {!error && !data && <p className="muted">Cargando grupos…</p>}
    {data && !data.groups.length && <p className="muted">No hay grupos activos configurados.</p>}
    {data?.groups?.length > 0 && <div className="organization-groups">
      {data.groups.map((group) => <article className="organization-group" key={group.id}>
        <header className="organization-group-heading">
          <div><h3>{group.name}</h3>{group.description && <p>{group.description}</p>}</div>
          <span>{group.members.length} miembro{group.members.length === 1 ? "" : "s"}</span>
        </header>
        {group.members.length ? <div className="organization-members">
          {group.members.map((member) => <div className="organization-member" key={member.id}>
            <div className="organization-member-person"><strong>{member.name}</strong></div>
            <div className="organization-member-roles">
              {member.roles.length ? member.roles.map((role) => <span key={role}>{role}</span>) : <span className="empty">Sin rol asignado</span>}
            </div>
            <div className={`organization-pending ${member.pending_actions ? "has-pending" : ""}`}>
              <strong>{member.pending_actions}</strong>
              <small>acción{member.pending_actions === 1 ? "" : "es"} pendiente{member.pending_actions === 1 ? "" : "s"}</small>
            </div>
          </div>)}
        </div> : <p className="muted organization-empty">Este grupo no tiene miembros activos.</p>}
      </article>)}
    </div>}
  </section>;
}
