import React, { useEffect, useState } from "react";
import ClosureDelegationButton from "./closure-delegation.jsx";
import OrganizationOverview from "./organization-overview.jsx";
import "./home-dashboard.css";

const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE_URL}${path}`;

const ACTION_LABELS = {
  APPROVAL_DECISION: "Responder aprobación",
  QUOTATION_VOTE: "Votar cotización",
  CLOSE_REQUEST: "Subir factura y cerrar",
  CORRECT_REQUEST: "Corregir y reenviar",
};

const statusName = (status) => ({
  SUBMITTED: "Enviada",
  PENDING_APPROVAL: "Pendiente de aprobación",
  QUOTATION_VOTING: "Votación de cotizaciones",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  NEEDS_REVISION: "Corrección solicitada",
  CANCELLED: "Cancelada",
  CLOSED: "Cerrada",
})[status] || String(status || "").replaceAll("_", " ").toLowerCase();

const urgencyName = (urgency) => ({
  LOW: "Baja",
  NORMAL: "Normal",
  HIGH: "Alta",
  CRITICAL: "Crítica",
})[urgency] || urgency;

const pendingAge = (value) => {
  if (!value) return "";
  const hours = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 3600000));
  if (hours < 1) return "Pendiente hace menos de 1 hora";
  if (hours < 24) return `Pendiente hace ${hours} hora(s)`;
  return `Pendiente hace ${Math.floor(hours / 24)} día(s)`;
};

async function dashboardApi(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const isFormData = options.body instanceof FormData;
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = "No se pudo completar la acción";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

async function openAttachment(attachment) {
  const popup = window.open("about:blank", "_blank");
  try {
    const response = await fetch(apiUrl(`/api/expenses/attachments/${attachment.id}`), {
      headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
    });
    if (!response.ok) throw new Error("No se pudo abrir el soporte");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    if (popup) {
      popup.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } else {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    }
  } catch (error) {
    popup?.close();
    throw error;
  }
}

function SupportLinks({ supports = [], onError }) {
  if (!supports.length) return <span className="pending-action-muted">Sin archivos adjuntos.</span>;
  return <div className="pending-support-list">{supports.map((file) => (
    <button
      className="pending-support-link"
      type="button"
      key={file.id}
      onClick={() => openAttachment(file).catch((error) => onError(error.message))}
    >
      {file.original_name}
    </button>
  ))}</div>;
}

function ApprovalAction({ request, busy, onSubmit }) {
  const [comment, setComment] = useState("");
  return <section className="pending-action-block">
    <div><p className="pending-action-eyebrow">DECISIÓN DE APROBACIÓN</p><h3>Registra tu decisión</h3></div>
    <label className="pending-action-field">Comentario<textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Para enviar a revisión, indica qué debe corregir el solicitante" /></label>
    <div className="pending-action-buttons">
      <button className="pending-action-danger" disabled={busy} onClick={() => onSubmit("REJECTED", comment)}>Rechazar</button>
      <button className="pending-action-review" disabled={busy || comment.trim().length < 3} onClick={() => onSubmit("REVISION_REQUESTED", comment)}>Enviar a revisión</button>
      <button className="pending-action-primary" disabled={busy} onClick={() => onSubmit("APPROVED", comment)}>Aprobar</button>
    </div>
    {(request.item_url || request.supports?.length) && <div className="pending-supports"><strong>Soportes</strong>{request.item_url && <a href={request.item_url} target="_blank" rel="noreferrer">Ver cotización en línea</a>}</div>}
  </section>;
}

function QuotationVoteAction({ request, busy, onVote, onError }) {
  return <section className="pending-action-block">
    <div><p className="pending-action-eyebrow">VOTACIÓN DE COTIZACIONES</p><h3>Selecciona una opción</h3></div>
    <div className="pending-quote-grid">{request.quotation_options.map((option) => (
      <article className="pending-quote-card" key={option.id}>
        <div className="pending-quote-heading"><strong>Opción {option.option_number}: {option.supplier}</strong><span>${Number(option.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
        {option.notes && <p>{option.notes}</p>}
        <div className="pending-supports">
          {option.item_url && <a href={option.item_url} target="_blank" rel="noreferrer">Ver cotización en línea</a>}
          <SupportLinks supports={option.supports} onError={onError} />
        </div>
        <button className="pending-action-primary" disabled={busy} onClick={() => onVote(option.id)}>Votar por esta opción</button>
      </article>
    ))}</div>
  </section>;
}

function CloseRequestAction({ request, busy, onCloseRequest, onDelegationChanged }) {
  const [invoice, setInvoice] = useState(null);
  const [notes, setNotes] = useState("");
  const submit = (event) => {
    event.preventDefault();
    if (invoice) onCloseRequest(invoice, notes);
  };
  return <section className="pending-action-block">
    <div><p className="pending-action-eyebrow">CIERRE DE SOLICITUD</p><h3>Sube la factura y cierra el expediente</h3></div>
    <form className="pending-action-form" onSubmit={submit}>
      <label className="pending-action-field">Factura<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" required onChange={(event) => setInvoice(event.target.files?.[0] || null)} /></label>
      <label className="pending-action-field">Notas de cierre<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Opcional" /></label>
      <div className="pending-action-buttons">
        {request.can_delegate_close && <ClosureDelegationButton
          expense={request}
          api={dashboardApi}
          onChanged={onDelegationChanged}
          buttonClassName="pending-action-secondary"
          overlayClassName="confirm-overlay pending-action-delegation-overlay"
        />}
        <button className="pending-action-primary" disabled={busy || !invoice}>Subir factura y cerrar</button>
      </div>
    </form>
  </section>;
}

function CorrectRequestAction({ busy, onOpenRequests }) {
  return <section className="pending-action-block">
    <div><p className="pending-action-eyebrow">CORRECCIÓN REQUERIDA</p><h3>La solicitud necesita cambios antes de continuar</h3></div>
    <p className="pending-action-muted">Abre la solicitud para revisar el comentario de revisión, modificarla y reenviarla conservando su tipo de flujo.</p>
    <div className="pending-action-buttons"><button className="pending-action-primary" disabled={busy} onClick={onOpenRequests}>Abrir para corregir / reenviar</button></div>
  </section>;
}

function PendingActionModal({ detail, loading, error, busy, message, onClose, onReload, onDelegationChanged, onOpenRequests, onError }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const request = detail?.request;
  const codes = new Set((detail?.actions || []).map((item) => item.code));

  const submitApproval = async (decision, comment) => {
    await onReload(() => dashboardApi(`/api/expenses/${request.request_id}/approval-decision`, {
      method: "POST",
      body: JSON.stringify({ decision, comment: comment.trim() || null }),
    }));
  };
  const submitVote = async (quotationOptionId) => {
    await onReload(() => dashboardApi(`/api/expenses/${request.request_id}/quotation-vote`, {
      method: "POST",
      body: JSON.stringify({ quotation_option_id: quotationOptionId }),
    }));
  };
  const closeRequest = async (invoice, notes) => {
    const body = new FormData();
    body.append("invoice", invoice);
    if (notes.trim()) body.append("notes", notes.trim());
    await onReload(() => dashboardApi(`/api/expenses/${request.request_id}/close`, { method: "POST", body }));
  };

  return <div className="pending-action-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="pending-action-modal" role="dialog" aria-modal="true" aria-labelledby="pending-action-title">
      <header className="pending-action-header">
        <div><p className="pending-action-eyebrow">ACCIÓN PENDIENTE</p><h2 id="pending-action-title">{request?.title || "Cargando solicitud..."}</h2>{request && <p className="pending-action-muted">{request.display_id} · {statusName(request.status)}</p>}</div>
        <button className="pending-action-close" type="button" onClick={onClose} aria-label="Cerrar">×</button>
      </header>
      {loading && <div className="pending-action-state">Cargando acciones vigentes...</div>}
      {error && <div className="pending-action-error">{error}</div>}
      {message && <div className="pending-action-success">{message}</div>}
      {request && <>
        <div className="pending-request-summary">
          <div><span>Urgencia</span><strong>{urgencyName(request.urgency)}</strong></div>
          {request.amount && <div><span>Monto</span><strong>${Number(request.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></div>}
          {request.supplier && <div><span>Proveedor</span><strong>{request.supplier}</strong></div>}
          <div><span>Flujo</span><strong>{request.request_type === "MULTI_QUOTE" ? "Múltiples cotizaciones" : "Solicitud sencilla"}</strong></div>
        </div>
        <p className="pending-request-description">{request.description}</p>
        {request.supports?.length > 0 && <div className="pending-supports"><strong>Soportes generales</strong><SupportLinks supports={request.supports} onError={onError} /></div>}
        {!detail.actions.length && !loading && <div className="pending-action-state">Ya no tienes acciones pendientes para esta solicitud.</div>}
        {codes.has("APPROVAL_DECISION") && <ApprovalAction request={request} busy={busy} onSubmit={(decision, comment) => submitApproval(decision, comment).catch((e) => onError(e.message))} />}
        {codes.has("QUOTATION_VOTE") && <QuotationVoteAction request={request} busy={busy} onVote={(id) => submitVote(id).catch((e) => onError(e.message))} onError={onError} />}
        {codes.has("CLOSE_REQUEST") && <CloseRequestAction request={request} busy={busy} onDelegationChanged={onDelegationChanged} onCloseRequest={(invoice, notes) => closeRequest(invoice, notes).catch((e) => onError(e.message))} />}
        {codes.has("CORRECT_REQUEST") && <CorrectRequestAction busy={busy} onOpenRequests={() => { onClose(); onOpenRequests(request.request_id, "CORRECT_REQUEST"); }} />}
      </>}
    </section>
  </div>;
}

export default function HomeDashboard({ refreshKey, onOpenRequests }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [modalError, setModalError] = useState("");
  const [modalMessage, setModalMessage] = useState("");
  const [loadingAction, setLoadingAction] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadDashboard = async () => {
    try {
      setError("");
      setData(await dashboardApi("/api/expenses/dashboard"));
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { loadDashboard(); }, [refreshKey]);

  const loadDetail = async (requestId) => {
    setLoadingAction(true);
    setModalError("");
    try {
      const result = await dashboardApi(`/api/expenses/${requestId}/my-actions`);
      setDetail(result);
      return result;
    } catch (e) {
      setModalError(e.message);
      throw e;
    } finally {
      setLoadingAction(false);
    }
  };

  const openAction = async (item) => {
    setSelected(item);
    setDetail(null);
    setModalMessage("");
    setModalError("");
    try { await loadDetail(item.request_id); } catch (_) {}
  };

  const performAndReload = async (operation) => {
    setBusy(true);
    setModalError("");
    setModalMessage("");
    try {
      await operation();
      setModalMessage("Acción registrada correctamente.");
      await Promise.all([loadDashboard(), loadDetail(selected.request_id)]);
    } catch (e) {
      setModalError(e.message);
      throw e;
    } finally {
      setBusy(false);
    }
  };

  const reloadAfterDelegation = async () => {
    setModalError("");
    setModalMessage("Delegación de cierre actualizada correctamente.");
    try {
      await Promise.all([loadDashboard(), loadDetail(selected.request_id)]);
    } catch (e) {
      setModalError(e.message);
    }
  };

  if (error) return <section className="card"><div className="notice error">{error}</div></section>;
  if (!data) return <section className="card"><p className="muted">Cargando resumen...</p></section>;

  const month = data.last_31_days;
  return <>
    <div className="dashboard-layout">
      <section className="dashboard-kpis">
        <article className="dashboard-kpi attention"><span>Acciones que requieren mi atención</span><strong>{data.pending_my_action}</strong><small>Acciones de flujo que esperan tu respuesta</small></article>
        <article className="dashboard-kpi"><span>Solicitudes en proceso</span><strong>{data.in_process}</strong><small>Abiertas actualmente</small></article>
        <article className="dashboard-kpi success"><span>Cerradas en 24 horas</span><strong>{data.closed_last_24h}</strong></article>
      </section>
      <section className="card dashboard-month"><div className="card-heading"><div><p className="eyebrow">ÚLTIMOS 31 DÍAS</p><h2>Resumen de solicitudes</h2></div></div>
        <div className="month-stat-grid"><div><span>Creadas</span><strong>{month.created}</strong></div><div><span>Aprobadas</span><strong>{month.approved}</strong></div><div><span>Cerradas</span><strong>{month.closed}</strong></div><div><span>Rechazadas</span><strong>{month.rejected}</strong></div><div><span>Canceladas</span><strong>{month.cancelled}</strong></div><div><span>Monto aprobado</span><strong>${Number(month.approved_amount).toLocaleString(undefined,{minimumFractionDigits:2})}</strong></div></div>
      </section>
      <section className="card dashboard-pending"><div className="card-heading"><div><p className="eyebrow">REQUIERE TU ATENCIÓN</p><h2>Acciones pendientes</h2></div><button className="secondary" onClick={onOpenRequests}>Ver todas</button></div>
        {data.pending_items.length ? <div className="dashboard-request-list">{data.pending_items.map((item) => <button key={item.request_id} onClick={() => openAction(item)}><span><strong>{item.title}</strong><small>{item.display_id} · {(item.actions || []).map((code) => ACTION_LABELS[code] || code).join(" · ") || statusName(item.status)}</small></span><span className={`urgency-badge urgency-${String(item.urgency).toLowerCase()}`}>{urgencyName(item.urgency)}</span><time>{pendingAge(item.created_at)}</time></button>)}</div> : <p className="muted">No tienes acciones pendientes.</p>}
      </section>
      <OrganizationOverview refreshKey={refreshKey} />
    </div>
    {selected && <PendingActionModal
      detail={detail}
      loading={loadingAction}
      error={modalError}
      busy={busy}
      message={modalMessage}
      onClose={() => { if (!busy) { setSelected(null); setDetail(null); setModalError(""); setModalMessage(""); } }}
      onReload={performAndReload}
      onDelegationChanged={reloadAfterDelegation}
      onOpenRequests={onOpenRequests}
      onError={setModalError}
    />}
  </>;
}
