import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Analytics } from "@vercel/analytics/react";
import "./styles.css";

const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(
  /\/$/,
  "",
);
const apiUrl = (path) => `${API_BASE_URL}${path}`;
const subcategoryName = (value) => value;
const descriptor = (value) => String(value || "")
  .replaceAll("_", " ")
  .toLowerCase()
  .replace(/^./, (letter) => letter.toUpperCase());
const roles = [
  ["REQUESTER", "Puede solicitar"],
  ["APPROVER", "Puede aprobar"],
  ["VIEWER", "Puede consultar"],
  ["ADMIN", "Administrador"],
];
const roleName = (role) => roles.find(([value]) => value === role)?.[1] || descriptor(role);
const userTitles = [
  ["PRESIDENTE", "Presidente"],
  ["VICEPRESIDENTE", "Vicepresidente"],
  ["TESORERO", "Tesorero"],
  ["VOCERO", "Vocero"],
  ["ADMINISTRADORA", "Administrador"],
  ["SIN_ASIGNAR", "Sin cargo asignado"],
];
const allowedAccessTitles = new Set(["PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "VOCERO", "ADMINISTRADORA"]);
const titleName = (title) =>
  title === "ADMIN_SISTEMA"
    ? "Administrador del sistema"
    : userTitles.find(([value]) => value === title)?.[1] || descriptor(title);

const personTypeName = (type) => ({
  OWNER: "Propietario",
  CO_OWNER: "Co-propietario",
  CONCIERGE: "Conserje",
  ADMINISTRATOR: "Administrador",
})[type] || descriptor(type);

const statusName = (status) => ({
  SUBMITTED: "Enviada",
  PENDING: "Pendiente",
  PENDING_APPROVAL: "Pendiente de aprobación",
  QUOTATION_VOTING: "Votación de cotizaciones",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  REVISION_REQUESTED: "Corrección solicitada",
  EXPIRED: "Ya no requerida",
  CANCELLED: "Cancelada",
  CLOSED: "Cerrada",
})[status] || descriptor(status);
const urgencyName = (urgency) => ({
  LOW: "Baja", NORMAL: "Normal", HIGH: "Alta", CRITICAL: "Crítica",
})[urgency] || descriptor(urgency);

const fieldName = (field) => ({
  name: "Nombre completo", identity_document: "Identificación", email: "Correo",
  phone: "Teléfono", person_type: "Tipo de persona", active: "Estado",
  title: "Cargo", apartments: "Apartamentos", can_request: "Puede solicitar",
  can_approve: "Puede aprobar", can_view: "Puede consultar",
  can_configure: "Puede configurar",
})[field] || descriptor(field);

const hasUnsavedChanges = () => Boolean(document.querySelector('[data-unsaved="true"]'));
const confirmDiscardChanges = () => !hasUnsavedChanges() || window.confirm("¿Deseas salir sin guardar? Los cambios realizados se perderán.");

function protectAnalyticsEvent(event) {
  try {
    if (new URL(event.url).pathname.startsWith("/approve/")) return null;
  } catch (_) {
    return null;
  }
  return event;
}

function latestExpenseVersions(items) {
  const byReference = new Map();
  for (const item of items) {
    byReference.set(item.request_id, item);
    byReference.set(item.display_id, item);
  }
  const rootOf = (item) => {
    let current = item,
      guard = 0;
    while (
      current.revised_from_request_id &&
      byReference.has(current.revised_from_request_id) &&
      guard++ < 100
    )
      current = byReference.get(current.revised_from_request_id);
    return current.request_id;
  };
  const latest = new Map();
  for (const item of items) {
    const root = rootOf(item),
      saved = latest.get(root);
    if (!saved || Number(item.id) > Number(saved.id)) latest.set(root, item);
  }
  return [...latest.values()];
}

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    console.error("Error al renderizar la aplicación", error, info);
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="single">
        <section className="card login-card">
          <p className="eyebrow">ERROR DE CARGA</p>
          <h1>No se pudo mostrar la aplicación</h1>
          <p className="muted">
            Recarga la página. Si el problema continúa, comparte el error
            mostrado en la consola del navegador.
          </p>
          <button className="primary" onClick={() => window.location.reload()}>
            Recargar
          </button>
        </section>
      </main>
    );
  }
}

async function api(path, options = {}) {
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
    let detail = "Ocurrió un error";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((item) => {
            const field = Array.isArray(item.loc)
              ? item.loc.filter((part) => part !== "body").join(".")
              : "";
            return `${field ? `${field}: ` : ""}${item.msg || "Valor inválido"}`;
          })
          .join(" ");
      } else if (payload.detail) {
        detail = payload.detail.message || JSON.stringify(payload.detail);
      }
    } catch (_) {}
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

const SESSION_IDLE_MS = 30 * 60 * 1000;
const ACTIVITY_SYNC_MS = 60 * 1000;

async function downloadAttachment(attachment) {
  const { url } = await loadAttachment(attachment);
  const link = document.createElement("a");
  link.href = url;
  link.download = attachment.original_name;
  link.click();
  URL.revokeObjectURL(url);
}

async function loadAttachment(attachment) {
  const response = await fetch(
    apiUrl(`/api/expenses/attachments/${attachment.id}`),
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    },
  );
  if (!response.ok) throw new Error("No se pudo abrir el archivo");
  const blob = await response.blob();
  return { attachment, url: URL.createObjectURL(blob), contentType: blob.type || attachment.content_type };
}

function AttachmentViewer({ file, onClose }) {
  useEffect(() => () => URL.revokeObjectURL(file.url), [file.url]);
  const download = () => {
    const link = document.createElement("a"); link.href = file.url;
    link.download = file.attachment.original_name; link.click();
  };
  const isImage = file.contentType.startsWith("image/");
  const isPdf = file.contentType === "application/pdf";
  return <div className="document-overlay" role="dialog" aria-modal="true" aria-label={`Visor de ${file.attachment.original_name}`}>
    <section className="document-viewer">
      <div className="document-toolbar"><div><p className="eyebrow">VISOR DE DOCUMENTOS</p><strong>{file.attachment.original_name}</strong></div>
        <div className="row-actions"><button className="secondary" onClick={download}>Descargar</button><button className="primary" onClick={onClose}>Cerrar</button></div>
      </div>
      <div className="document-content">
        {isPdf ? <iframe src={file.url} title={file.attachment.original_name} /> : isImage ? <img src={file.url} alt={file.attachment.original_name} /> :
          <div className="document-unsupported"><p>Este formato no puede visualizarse en el navegador.</p><button className="primary" onClick={download}>Descargar archivo</button></div>}
      </div>
    </section>
  </div>;
}

function Login({ onLogin }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      const result = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(form),
      });
      localStorage.setItem("access_token", result.access_token);
      onLogin(result.user);
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <main className="single">
      <section className="card login-card">
        <div className="brand-mark dark">PH</div>
        <p className="eyebrow">GESTIÓN DE GASTOS</p>
        <h1>Iniciar sesión</h1>
        <p className="muted">
          Accede con el usuario registrado por el administrador.
        </p>
        <form onSubmit={submit} className="login-form">
          <label>
            Correo
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength="8"
            />
          </label>
          {error && <div className="notice error">{error}</div>}
          <button className="primary">Entrar</button>
        </form>
      </section>
    </main>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${String(status).toLowerCase()}`}>
      {statusName(status)}
    </span>
  );
}

function ChangePassword({ user, onChanged }) {
  const [form, setForm] = useState({
      current_password: "",
      new_password: "",
      confirmation: "",
    }),
    [saving, setSaving] = useState(false),
    [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.new_password !== form.confirmation) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setSaving(true);
    try {
      const result = await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: form.current_password,
          new_password: form.new_password,
        }),
      });
      localStorage.setItem("access_token", result.access_token);
      onChanged(result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <main className="single">
      <section className="card login-card">
        <div className="brand-mark dark">PH</div>
        <p className="eyebrow">PRIMER INICIO DE SESIÓN</p>
        <h1>Crea tu contraseña</h1>
        <p className="muted">
          Hola {user.name}. Reemplaza la contraseña temporal que recibiste por
          correo antes de continuar.
        </p>
        <form className="login-form" onSubmit={submit}>
          <label>
            Contraseña temporal
            <input
              type="password"
              value={form.current_password}
              onChange={(e) =>
                setForm({ ...form, current_password: e.target.value })
              }
              required
              minLength="8"
              autoComplete="current-password"
            />
          </label>
          <label>
            Nueva contraseña
            <input
              type="password"
              value={form.new_password}
              onChange={(e) =>
                setForm({ ...form, new_password: e.target.value })
              }
              required
              minLength="10"
              maxLength="128"
              autoComplete="new-password"
            />
          </label>
          <label>
            Confirmar nueva contraseña
            <input
              type="password"
              value={form.confirmation}
              onChange={(e) =>
                setForm({ ...form, confirmation: e.target.value })
              }
              required
              minLength="10"
              maxLength="128"
              autoComplete="new-password"
            />
          </label>
          {error && <div className="notice error">{error}</div>}
          <button className="primary" disabled={saving}>
            {saving ? "Guardando..." : "Guardar contraseña"}
          </button>
        </form>
      </section>
    </main>
  );
}

function ExpenseForm({
  onCreated,
  draft,
  onCancelEdit,
  categoryOptions = [],
  subcategoryOptions = {},
}) {
  const [requestType, setRequestType] = useState("SIMPLE");
  const [quoteOptions, setQuoteOptions] = useState([
    { supplier: "", amount: "", item_url: "", notes: "", file: null },
    { supplier: "", amount: "", item_url: "", notes: "", file: null },
  ]);
  const firstType = categoryOptions[0]?.[0] || "",
    firstSub = subcategoryOptions[firstType]?.[0]?.[0] || "";
  const empty = {
    title: "",
    description: "",
    expense_type: firstType,
    expense_subcategory: firstSub,
    urgency: "NORMAL",
    amount: "",
    supplier: "",
    item_url: "",
  };
  const [form, setForm] = useState(empty);
  const [quotation, setQuotation] = useState(null);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (draft) {
      setForm({
        title: draft.title,
        description: draft.description,
        expense_type: draft.expense_type,
        expense_subcategory: draft.expense_subcategory,
        urgency: draft.urgency || "NORMAL",
        amount: String(draft.amount),
        supplier: draft.supplier,
        item_url: draft.item_url || "",
        revised_from_request_id: draft.request_id,
      });
      setQuotation(null);
      setMessage(null);
    } else if (categoryOptions.length) {
      const expense_type = categoryOptions[0][0];
      setForm((current) =>
        current.expense_type
          ? current
          : {
              ...current,
              expense_type,
              expense_subcategory:
                subcategoryOptions[expense_type]?.[0]?.[0] || "",
            },
      );
    }
  }, [draft?.request_id, categoryOptions.length]);
  const expenseDirty = Boolean(quotation) || (draft
    ? ["title", "description", "expense_type", "expense_subcategory", "urgency", "supplier", "item_url"].some((key) => String(form[key] || "") !== String(draft[key] || "")) || String(form.amount || "") !== String(draft.amount || "")
    : ["title", "description", "amount", "supplier", "item_url"].some((key) => String(form[key] || "").trim()));
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    if (requestType === "SIMPLE" && !form.item_url && !quotation) {
      setMessage({
        type: "error",
        text: "Debes proporcionar una URL o adjuntar una cotización.",
      });
      setSaving(false);
      return;
    }
    if (requestType === "MULTI_QUOTE" && quoteOptions.some((option) => !option.item_url && !option.file)) {
      setMessage({ type: "error", text: "Cada cotización debe incluir una URL o un archivo adjunto." });
      setSaving(false);
      return;
    }
    if (requestType === "MULTI_QUOTE") {
      const urls = quoteOptions.filter((option) => option.item_url).map((option) => {
        const parsed = new URL(option.item_url.trim()); parsed.hash = "";
        return parsed.toString().replace(/\/$/, "");
      });
      if (new Set(urls).size !== urls.length) {
        setMessage({ type: "error", text: "Cada opción debe utilizar una URL de cotización diferente." });
        setSaving(false);
        return;
      }
      const fileNames = quoteOptions.filter((option) => option.file).map((option) => option.file.name.trim().toLowerCase());
      if (new Set(fileNames).size !== fileNames.length) {
        setMessage({ type: "error", text: "Cada opción debe utilizar un archivo con nombre diferente." });
        setSaving(false);
        return;
      }
    }
    let item = null;
    try {
      const payload = {
        ...form,
        request_type: requestType,
        amount: requestType === "SIMPLE" ? Number(form.amount) : null,
        supplier: requestType === "SIMPLE" ? form.supplier : null,
        item_url: form.item_url || null,
        quotation_pending: Boolean(quotation),
        quotation_options: requestType === "MULTI_QUOTE" ? quoteOptions.map((option) => ({
          supplier: option.supplier, amount: Number(option.amount), item_url: option.item_url || null,
          notes: option.notes || null, attachment_pending: Boolean(option.file),
        })) : [],
      };
      const editing = Boolean(draft);
      delete payload.revised_from_request_id;
      item = await api(
        editing
          ? `/api/expenses/${draft.request_id}/resubmit`
          : "/api/expenses",
        { method: editing ? "PUT" : "POST", body: JSON.stringify(payload) },
      );
      if (requestType === "SIMPLE" && quotation) {
        const data = new FormData();
        data.append("file", quotation);
        await api(`/api/expenses/${item.request_id}/attachments`, {
          method: "POST",
          body: data,
        });
      }
      if (requestType === "MULTI_QUOTE") {
        for (let index = 0; index < quoteOptions.length; index += 1) {
          if (!quoteOptions[index].file) continue;
          const data = new FormData(); data.append("file", quoteOptions[index].file);
          await api(`/api/expenses/${item.request_id}/quotation-options/${item.quotation_options[index].id}/attachment`, { method: "POST", body: data });
        }
      }
      setForm(empty);
      setQuotation(null);
      setQuoteOptions([{ supplier: "", amount: "", item_url: "", notes: "", file: null }, { supplier: "", amount: "", item_url: "", notes: "", file: null }]);
      e.target.reset();
      setMessage({
        type: "success",
        text: `Solicitud ${item.display_id} enviada a aprobación con sus soportes.`,
      });
      onCreated();
    } catch (err) {
      setMessage({
        type: "error",
        text: item
          ? `La solicitud ${item.display_id} se guardó, pero el archivo no pudo cargarse: ${err.message}`
          : err.message,
      });
      onCreated();
    } finally {
      setSaving(false);
    }
  };
  return (
    <section className="card" id="expense-form">
      <span hidden data-unsaved={expenseDirty ? "true" : "false"} />
      <div className="card-heading">
        <div>
          <p className="eyebrow">
            {draft ? "CORRECCIÓN Y REENVÍO" : "NUEVA SOLICITUD"}
          </p>
          <h2>{draft ? "Corregir solicitud existente" : "Registrar gasto"}</h2>
        </div>
        {draft && (
          <button
            className="secondary"
            type="button"
            onClick={() => {
              setForm(empty);
              onCancelEdit?.();
            }}
          >
            Cancelar edición
          </button>
        )}
      </div>
      {draft && (
        <div className="revision-notice">
          Se actualizará la solicitud <strong>{draft.display_id}</strong> sin
          crear otra fila. El flujo anterior se invalidará y se generarán enlaces de
          aprobación nuevos.
        </div>
      )}
      {!draft && <div className="request-type-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={requestType === "SIMPLE"} className={requestType === "SIMPLE" ? "active" : ""} onClick={() => setRequestType("SIMPLE")}>Solicitud sencilla</button>
        <button type="button" role="tab" aria-selected={requestType === "MULTI_QUOTE"} className={requestType === "MULTI_QUOTE" ? "active" : ""} onClick={() => setRequestType("MULTI_QUOTE")}>Múltiples cotizaciones</button>
      </div>}
      <form onSubmit={submit} className="form-grid">
        <label className="full">
          Título
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
            minLength="3"
          />
        </label>
        <label>
          Categoría
          <select
            value={form.expense_type}
            onChange={(e) => {
              const type = e.target.value;
              setForm({
                ...form,
                expense_type: type,
                expense_subcategory: subcategoryOptions[type]?.[0]?.[0] || "",
              });
            }}
          >
            {categoryOptions.map((x) => (
              <option key={x[0]} value={x[0]}>
                {x[1]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Subcategoría
          <select
            value={form.expense_subcategory}
            onChange={(e) =>
              setForm({ ...form, expense_subcategory: e.target.value })
            }
          >
            {(subcategoryOptions[form.expense_type] || []).map((x) => (
              <option key={x[0]} value={x[0]}>
                {x[1]}
              </option>
            ))}
          </select>
        </label>
        {requestType === "SIMPLE" && <label>
          Monto (USD)
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            required
          />
        </label>}
        <label>
          Nivel de urgencia
          <select value={form.urgency} onChange={(e) => setForm({ ...form, urgency: e.target.value })}>
            <option value="LOW">Baja</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">Alta</option>
            <option value="CRITICAL">Crítica</option>
          </select>
        </label>
        {requestType === "SIMPLE" && <label className="full">
          Proveedor
          <input
            value={form.supplier}
            onChange={(e) => setForm({ ...form, supplier: e.target.value })}
            required
            minLength="2"
          />
        </label>}
        {requestType === "SIMPLE" && <div className="full support-requirement">
          Adjunta al menos un soporte para iniciar el flujo: URL, cotización o
          ambos.
        </div>}
        {requestType === "SIMPLE" && <label>
          URL del producto o servicio
          <input
            type="url"
            value={form.item_url}
            onChange={(e) => setForm({ ...form, item_url: e.target.value })}
            placeholder="https://..."
          />
        </label>}
        {requestType === "SIMPLE" && <label>
          Cotización (PDF o imagen, máx. 10 MB)
          <input
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp"
            onChange={(e) => setQuotation(e.target.files[0] || null)}
          />
        </label>}
        {requestType === "MULTI_QUOTE" && <div className="full quote-options-editor">
          <div className="card-heading"><div><h3>Opciones para votación</h3><span className="muted">Agrega al menos dos proveedores. Cada opción requiere una URL o un archivo.</span></div><button type="button" className="secondary" onClick={() => setQuoteOptions([...quoteOptions, { supplier: "", amount: "", item_url: "", notes: "", file: null }])}>Agregar opción</button></div>
          {quoteOptions.map((option, index) => <fieldset className="quote-option-card" key={index}>
            <legend>Opción {index + 1}</legend>
            <label>Proveedor<input required minLength="2" value={option.supplier} onChange={(e) => setQuoteOptions(quoteOptions.map((item, i) => i === index ? {...item, supplier:e.target.value} : item))}/></label>
            <label>Monto (USD)<input required type="number" min="0.01" step="0.01" value={option.amount} onChange={(e) => setQuoteOptions(quoteOptions.map((item, i) => i === index ? {...item, amount:e.target.value} : item))}/></label>
            <label>URL de cotización<input type="url" placeholder="https://..." value={option.item_url} onChange={(e) => setQuoteOptions(quoteOptions.map((item, i) => i === index ? {...item, item_url:e.target.value} : item))}/></label>
            <label>Archivo (PDF, PNG, JPG o WEBP)<input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setQuoteOptions(quoteOptions.map((item, i) => i === index ? {...item, file:e.target.files[0] || null} : item))}/></label>
            <label>Observaciones<input value={option.notes} onChange={(e) => setQuoteOptions(quoteOptions.map((item, i) => i === index ? {...item, notes:e.target.value} : item))}/></label>
            {quoteOptions.length > 2 && <button type="button" className="danger-link" onClick={() => setQuoteOptions(quoteOptions.filter((_, i) => i !== index))}>Eliminar opción</button>}
          </fieldset>)}
        </div>}
        <label className="full">
          Descripción / justificación
          <textarea
            rows="4"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
            minLength="3"
          />
        </label>
        <div className="full form-actions">
          {message && (
            <div className={`notice ${message.type}`}>{message.text}</div>
          )}
          <button
            className="primary"
            disabled={
              saving || !categoryOptions.length || !form.expense_subcategory
            }
          >
            {saving
              ? "Guardando..."
              : draft
                ? "Guardar y reenviar"
                : "Crear solicitud"}
          </button>
        </div>
      </form>
    </section>
  );
}

function ClosurePanel({ expense, onDone, onCancel }) {
  const [invoice, setInvoice] = useState(null),
    [notes, setNotes] = useState(""),
    [saving, setSaving] = useState(false),
    [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const data = new FormData();
      data.append("invoice", invoice);
      if (notes) data.append("notes", notes);
      await api(`/api/expenses/${expense.request_id}/close`, {
        method: "POST",
        body: data,
      });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <form className="closure-panel" onSubmit={submit}>
      <div>
        <p className="eyebrow">CIERRE DE APROBACIÓN</p>
        <h3>{expense.title}</h3>
        <span className="muted">
          Adjunta la factura final para cerrar esta solicitud aprobada.
        </span>
      </div>
      <label>
        Factura
        <input
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          onChange={(e) => setInvoice(e.target.files[0] || null)}
          required
        />
      </label>
      <label>
        Notas de cierre
        <textarea
          rows="2"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      {error && <div className="notice error">{error}</div>}
      <div className="closure-actions">
        <button type="button" className="secondary" onClick={onCancel}>
          Cancelar
        </button>
        <button className="primary" disabled={saving}>
          {saving ? "Cerrando..." : "Cerrar aprobación"}
        </button>
      </div>
    </form>
  );
}

const answeredApprovalStatuses = new Set(["APPROVED", "REJECTED", "REVISION_REQUESTED"]);
const flowMetrics = (approvals = []) => {
  const answered = approvals.filter((item) => answeredApprovalStatuses.has(item.status)).length;
  const pending = approvals.filter((item) => ["PENDING", "WAITING"].includes(item.status)).length;
  return { answered, pending, total: approvals.length, percentage: approvals.length ? Math.round(answered * 100 / approvals.length) : 0 };
};
const expenseFlowMetrics = (expense) => {
  if (expense.request_type !== "MULTI_QUOTE") return flowMetrics(expense.approvals);
  const answered = expense.quotation_votes?.length || 0;
  const total = Math.max(Number(expense.quotation_voter_count) || 0, answered);
  return {
    answered,
    pending: Math.max(0, total - answered),
    total,
    percentage: total ? Math.round(answered * 100 / total) : 0,
  };
};
const APP_TIME_ZONE = import.meta.env.VITE_TIME_ZONE || "America/Panama";
const approvalTimestamp = (value) => value ? new Date(value).toLocaleString("es-PA", {
  dateStyle: "medium",
  timeStyle: "medium",
  timeZone: APP_TIME_ZONE,
}) : "Pendiente";
const panamaDate = (value) => value ? new Date(value).toLocaleDateString("es-PA", {
  timeZone: APP_TIME_ZONE,
}) : "—";
const pendingAge = (value) => {
  if (!value) return "";
  const hours = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 3600000));
  if (hours < 1) return "Pendiente hace menos de 1 hora";
  if (hours < 24) return `Pendiente hace ${hours} hora(s)`;
  return `Pendiente hace ${Math.floor(hours / 24)} día(s)`;
};
const flowEventName = (event) => ({
  REQUEST_CREATED: "Solicitud creada",
  STEP_CREATED: "Paso de aprobación creado",
  STEP_ACTIVATED: "Paso de aprobación activado",
  STEP_APPROVED: "Aprobación recibida",
  STEP_REJECTED: "Rechazo recibido",
  STEP_REVISION_REQUESTED: "Corrección solicitada",
  STEP_EXPIRED: "Aprobación ya no requerida",
  REQUEST_CANCELLED: "Solicitud cancelada",
  REQUEST_CLOSED: "Solicitud cerrada",
  EXPENSE_CREATED: "Solicitud creada",
  EXPENSE_UPDATED: "Solicitud actualizada",
  EXPENSE_CLOSED: "Solicitud cerrada",
  EXPENSE_CANCELLED: "Solicitud cancelada",
})[event] || descriptor(event);

function FlowProgressViewer({ expense, onClose }) {
  const metrics = expenseFlowMetrics(expense);
  const multiQuote = expense.request_type === "MULTI_QUOTE";
  return <div className="confirm-overlay" role="presentation" onMouseDown={onClose}>
    <section className="confirm-dialog flow-progress-dialog" role="dialog" aria-modal="true" aria-labelledby="flow-progress-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="card-heading"><div><p className="eyebrow">AVANCE DEL FLUJO</p><h2 id="flow-progress-title">{expense.display_id}</h2><span className="muted">{expense.title}</span></div><button className="secondary" onClick={onClose}>Cerrar</button></div>
      <div className="flow-summary"><strong>{metrics.percentage}% respondido</strong><span>{metrics.answered} respuesta(s) · {metrics.pending} pendiente(s) · {metrics.total} participante(s)</span><div className="flow-progress-track"><span style={{width:`${metrics.percentage}%`}} /></div></div>
      <div className="flow-response-list">{multiQuote ? expense.quotation_votes.map((vote) => { const option = expense.quotation_options.find((item) => item.id === vote.quotation_option_id); return <article key={`${vote.voter_email}-${vote.quotation_option_id}`} className="flow-response-card">
        <div><strong>{vote.voter_name || vote.voter_email}</strong><span>{titleName(vote.voter_role)}</span></div>
        <StatusBadge status="APPROVED"/>
        <dl><div><dt>Respuesta</dt><dd>Votó por opción {option?.option_number || vote.quotation_option_id}{option?.supplier ? ` · ${option.supplier}` : ""}</dd></div><div><dt>Timestamp de respuesta</dt><dd>{approvalTimestamp(vote.updated_at || vote.created_at)}</dd></div></dl>
      </article> }) : expense.approvals.map((approval) => <article key={approval.id} className="flow-response-card">
        <div><strong>{approval.approver_name || approval.approver_email}</strong><span>{titleName(approval.approver_role)}</span></div>
        <StatusBadge status={approval.status}/>
        <dl><div><dt>Respuesta</dt><dd>{statusName(approval.status)}</dd></div><div><dt>Asignación</dt><dd>{approvalTimestamp(approval.created_at)}</dd></div><div><dt>Timestamp de respuesta</dt><dd>{approvalTimestamp(approval.decided_at)}</dd></div></dl>
        {["PENDING", "WAITING"].includes(approval.status) && <p className="flow-comment"><strong>{pendingAge(approval.created_at)}</strong></p>}
        {approval.comment && <p className="flow-comment"><strong>Comentario:</strong> {approval.comment}</p>}
      </article>)}</div>
    </section>
  </div>;
}

function ExpenseDetailViewer({ expense, categoryName, subcategoryName, canApprove, onVoted, onClose }) {
  const vote = async (optionId) => {
    await api(`/api/expenses/${expense.internal_request_id || expense.request_id}/quotation-vote`, { method: "POST", body: JSON.stringify({ quotation_option_id: optionId }) });
    onVoted?.(); onClose();
  };
  return <div className="confirm-overlay" role="presentation" onMouseDown={onClose}>
    <section className="confirm-dialog expense-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="expense-detail-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="card-heading"><div><p className="eyebrow">DETALLE DE LA SOLICITUD</p><h2 id="expense-detail-title">{expense.title}</h2><span className="muted">{expense.display_id}</span></div><button className="secondary" onClick={onClose}>Cerrar</button></div>
      <dl className="expense-detail-grid">
        <div><dt>Solicitante</dt><dd>{expense.requested_by}</dd></div>
        <div><dt>Proveedor</dt><dd>{expense.supplier}</dd></div>
        <div><dt>Categoría</dt><dd>{categoryName(expense.expense_type)}</dd></div>
        <div><dt>Subcategoría</dt><dd>{subcategoryName(expense.expense_subcategory) || "—"}</dd></div>
        <div><dt>Urgencia</dt><dd><span className={`urgency-badge urgency-${String(expense.urgency || "NORMAL").toLowerCase()}`}>{urgencyName(expense.urgency)}</span></dd></div>
        <div><dt>Monto</dt><dd>${Number(expense.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</dd></div>
        <div><dt>Estado</dt><dd>{statusName(expense.status)}</dd></div>
        <div><dt>Inicio</dt><dd>{approvalTimestamp(expense.created_at)}</dd></div>
        <div><dt>Última actualización</dt><dd>{flowEventName(expense.last_event_type)}<span className="subtext">{approvalTimestamp(expense.last_event_at)}</span></dd></div>
      </dl>
      {expense.request_type === "MULTI_QUOTE" && <div className="quotation-audit-list"><h3>Cotizaciones presentadas</h3>{expense.quotation_options.map((option) => { const count = expense.quotation_votes.filter((item) => item.quotation_option_id === option.id).length; return <article className={`quote-option-card ${expense.selected_quotation_id === option.id ? "selected" : ""}`} key={option.id}><div><strong>Opción {option.option_number}: {option.supplier}</strong><span className="subtext">${Number(option.amount).toLocaleString(undefined,{minimumFractionDigits:2})} · {count} voto(s)</span>{option.notes && <span className="subtext">{option.notes}</span>}</div>{option.item_url && <a href={option.item_url} target="_blank" rel="noreferrer">Ver cotización</a>}{canApprove && expense.status === "QUOTATION_VOTING" && <button className="primary" onClick={() => vote(option.id)}>Votar por esta opción</button>}</article> })}</div>}
      <div className="description-box"><strong>Descripción / justificación</strong><p>{expense.description}</p></div>
      <div className="expense-detail-references"><span><strong>ID:</strong> {expense.display_id}</span><span><strong>Flujo:</strong> {expense.flow_id}</span></div>
    </section>
  </div>;
}

function ExpenseTable({
  refreshKey,
  canEdit,
  canApprove,
  canClose,
  onEdit,
  onChanged,
  categoryOptions = [],
  subcategoryOptions = {},
}) {
  const expenseTypes = categoryOptions;
  const subcategoryName = (value) =>
    Object.values(subcategoryOptions)
      .flat()
      .find(([code]) => code === value)?.[1] || value;
  const categoryName = (value) => expenseTypes.find(([code]) => code === value)?.[1] || value;
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [urgency, setUrgency] = useState("");
  const [closing, setClosing] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [flowViewing, setFlowViewing] = useState(null);
  const [detailViewing, setDetailViewing] = useState(null);
  useEffect(() => {
    const loadExpenses = () => api("/api/expenses")
      .then((data) =>
        setItems(
          latestExpenseVersions(data).map((item) => ({
            ...item,
            approvals: item.approvals.filter((a) => a.flow_id === item.flow_id),
            internal_request_id: item.request_id,
            request_id: item.display_id,
          })),
        ),
      )
      .catch((e) => setError(e.message));
    loadExpenses();
    const timer = window.setInterval(loadExpenses, 5000);
    return () => window.clearInterval(timer);
  }, [refreshKey]);
  const cancel = async (expense) => {
    const reason = window.prompt(
      `Indica el motivo para cancelar "${expense.title}":`,
    );
    if (!reason) return;
    try {
      await api(`/api/expenses/${expense.request_id}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  const normalized = search.trim().toLowerCase();
  const filtered = items.filter(
    (x) =>
      (!status || x.status === status) &&
      (!category || x.expense_type === category) &&
      (!urgency || x.urgency === urgency) &&
      (!normalized ||
        [
          x.display_id,
          x.request_id,
          x.title,
          x.supplier,
          x.requested_by,
          x.flow_id,
        ].some((value) =>
          String(value || "")
            .toLowerCase()
            .includes(normalized),
        )),
  ).sort((a, b) => {
    const weight = { CRITICAL: 4, HIGH: 3, NORMAL: 2, LOW: 1 };
    return (weight[b.urgency] || 2) - (weight[a.urgency] || 2) || new Date(b.created_at) - new Date(a.created_at);
  });
  return (
    <section className="card">
      {viewing && <AttachmentViewer file={viewing} onClose={() => setViewing(null)} />}
      {flowViewing && <FlowProgressViewer expense={flowViewing} onClose={() => setFlowViewing(null)} />}
      {detailViewing && <ExpenseDetailViewer expense={detailViewing} categoryName={categoryName} subcategoryName={subcategoryName} canApprove={canApprove} onVoted={onChanged} onClose={() => setDetailViewing(null)} />}
      <div className="card-heading">
        <div>
          <p className="eyebrow">SEGUIMIENTO</p>
          <h2>Solicitudes</h2>
        </div>
      </div>
      {closing && (
        <ClosurePanel
          expense={closing}
          onCancel={() => setClosing(null)}
          onDone={() => {
            setClosing(null);
            onChanged();
          }}
        />
      )}
      <div className="table-filters">
        <label>
          Buscar
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="ID, solicitud, proveedor..."
          />
        </label>
        <label>
          Estado
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="SUBMITTED">Enviada</option>
            <option value="PENDING_APPROVAL">Pendiente</option>
            <option value="QUOTATION_VOTING">En votación</option>
            <option value="APPROVED">Aprobada</option>
            <option value="REJECTED">Rechazada</option>
            <option value="NEEDS_REVISION">Requiere revisión</option>
            <option value="CANCELLED">Cancelada</option>
            <option value="CLOSED">Cerrada</option>
          </select>
        </label>
        <label>
          Categoría
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Todas</option>
            {expenseTypes.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Urgencia
          <select value={urgency} onChange={(e) => setUrgency(e.target.value)}>
            <option value="">Todas</option>
            <option value="CRITICAL">Crítica</option>
            <option value="HIGH">Alta</option>
            <option value="NORMAL">Normal</option>
            <option value="LOW">Baja</option>
          </select>
        </label>
        {(search || status || category || urgency) && (
          <button
            className="secondary"
            onClick={() => {
              setSearch("");
              setStatus("");
              setCategory("");
              setUrgency("");
            }}
          >
            Limpiar
          </button>
        )}
        <span className="filter-count">
          {filtered.length} de {items.length}
        </span>
      </div>
      {error ? (
        <div className="notice error">{error}</div>
      ) : items.length === 0 ? (
        <p className="muted">Aún no hay solicitudes.</p>
      ) : filtered.length === 0 ? (
        <p className="muted">
          No hay solicitudes que coincidan con los filtros.
        </p>
      ) : (
        <div className="table-wrap">
          <table className="expenses-table">
            <colgroup>
              <col className="col-request" /><col className="col-start" /><col className="col-update" /><col className="col-category" />
              <col className="col-support" /><col className="col-invoice" /><col className="col-amount" />
              <col className="col-status" /><col className="col-flow" />{canEdit && <col className="col-actions" />}
            </colgroup>
            <thead>
              <tr>
                <th>Solicitud</th>
                <th>Inicio</th>
                <th>Última actualización</th>
                <th>Categoría</th>
                <th>Soportes</th>
                <th>Factura de cierre</th>
                <th>Monto</th>
                <th>Estado</th>
                <th>Avance del flujo</th>
                {canEdit && <th>Acción</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map((x) => (
                <tr key={x.request_id}>
                  <td className="request-cell">
                    <button className="request-detail-button" onClick={() => setDetailViewing(x)}>{x.title}</button>
                    <span className={`urgency-badge urgency-${String(x.urgency || "NORMAL").toLowerCase()}`}>{urgencyName(x.urgency)}</span>
                    <span className="subtext">{x.supplier}</span>
                    <span className="subtext id-code" title={x.request_id}>{x.request_id}</span>
                    {x.revised_from_request_id && <span className="subtext">Solicitud corregida</span>}
                  </td>
                  <td className="timestamp-cell">{approvalTimestamp(x.created_at)}</td>
                  <td className="timestamp-cell"><strong>{flowEventName(x.last_event_type)}</strong><span className="subtext">{approvalTimestamp(x.last_event_at)}</span></td>
                  <td>
                    {x.expense_type}
                    <span className="subtext">
                      {subcategoryName(x.expense_subcategory)}
                    </span>
                  </td>
                  <td className="support-cell">
                    {x.item_url && (
                      <a href={x.item_url} target="_blank" rel="noreferrer">
                        Ver producto/servicio
                      </a>
                    )}
                    {x.attachments.filter((a) => a.document_type !== "INVOICE").map((a) => (
                      <button
                        className="link-button"
                        key={a.id}
                        onClick={() => loadAttachment(a).then(setViewing).catch((e) => setError(e.message))}
                      >
                        {a.document_type === "PURCHASE_ORDER"
                          ? "Orden: "
                          : a.document_type === "INVOICE"
                            ? "Factura: "
                            : ""}
                        {a.original_name}
                      </button>
                    ))}
                    {!x.item_url && !x.attachments.some((a) => a.document_type !== "INVOICE") && (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td className="invoice-cell">
                    {x.status === "CLOSED" ? (
                      x.attachments.filter((a) => a.document_type === "INVOICE").map((a) => (
                        <button className="link-button" key={a.id} onClick={() => loadAttachment(a).then(setViewing).catch((e) => setError(e.message))}>
                          Ver factura
                          <span className="subtext">{a.original_name}</span>
                        </button>
                      ))
                    ) : <span className="muted">Disponible al cerrar</span>}
                    {x.status === "CLOSED" && !x.attachments.some((a) => a.document_type === "INVOICE") && <span className="muted">Sin factura registrada</span>}
                  </td>
                  <td className="amount-cell">
                    $
                    {Number(x.amount).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td>
                    <StatusBadge status={x.status} />
                    {x.cancellation_reason && (
                      <span className="subtext" title={x.cancellation_reason}>
                        Motivo: {x.cancellation_reason}
                      </span>
                    )}
                    {x.closed_by && (
                      <span className="subtext">Cerrada por {x.closed_by}</span>
                    )}
                  </td>
                  <td className="flow-cell">
                    {(() => { const progress=expenseFlowMetrics(x); return <button className="flow-progress-button" onClick={() => setFlowViewing(x)} aria-label={`Ver avance del flujo ${x.display_id}`}>
                      <span><strong>{progress.percentage}%</strong> respondido</span>
                      <div className="flow-progress-track"><span style={{width:`${progress.percentage}%`}} /></div>
                      <small>{progress.answered} respuesta(s) · {progress.pending} pendiente(s)</small>
                    </button> })()}
                  </td>
                  {canEdit && (
                    <td>
                      <div className="row-actions">
                        <button
                          className="secondary nowrap"
                          onClick={() => onEdit(x)}
                        >
                          Corregir / reenviar
                        </button>
                        {["SUBMITTED", "PENDING_APPROVAL", "APPROVED"].includes(
                          x.status,
                        ) && (
                          <button
                            className="danger nowrap"
                            onClick={() => cancel(x)}
                          >
                            Cancelar solicitud
                          </button>
                        )}
                        {canClose && x.status === "APPROVED" && (
                          <button
                            className="primary nowrap"
                            onClick={() => setClosing(x)}
                          >
                            Registrar factura y cerrar
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function CorrectionPicker({ refreshKey, onEdit }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api("/api/expenses").then((data) => setItems(latestExpenseVersions(data)));
  }, [refreshKey]);
  if (!items.length) return null;
  return (
    <section className="correction-bar">
      <span>¿Necesitas corregir una solicitud enviada?</span>
      <div>
        <select id="correction-request" defaultValue="">
          <option value="" disabled>
            Selecciona una solicitud
          </option>
          {items.map((x) => (
            <option key={x.request_id} value={x.request_id}>
              {x.title} · {statusName(x.status)} · {x.request_id.slice(0, 8)}
            </option>
          ))}
        </select>
        <button
          className="secondary nowrap"
          onClick={() => {
            const id = document.getElementById("correction-request").value;
            const item = items.find((x) => x.request_id === id);
            if (item) onEdit(item);
          }}
        >
          Corregir / reenviar
        </button>
      </div>
    </section>
  );
}

function Invoices({ categoryOptions = [] }) {
  const [items, setItems] = useState([]),
    [search, setSearch] = useState(""),
    [category, setCategory] = useState(""),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("q", search.trim());
      if (category) params.set("category", category);
      setItems(
        await api(`/api/expenses/invoices${params.size ? `?${params}` : ""}`),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);
  const submit = (e) => {
    e.preventDefault();
    load();
  };
  const clear = () => {
    setSearch("");
    setCategory("");
    setLoading(true);
    setError("");
    api("/api/expenses/invoices")
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };
  const download = (item) =>
    downloadAttachment({
      id: item.attachment_id,
      original_name: item.original_name,
    }).catch((e) => setError(e.message));
  return (
    <section className="card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">DOCUMENTOS FINALES</p>
          <h2>Facturas</h2>
        </div>
      </div>
      <form className="table-filters" onSubmit={submit}>
        <label>
          Buscar
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Factura, ID, proveedor, solicitante..."
          />
        </label>
        <label>
          Categoría
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Todas</option>
            {categoryOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button className="primary" disabled={loading}>
          {loading ? "Buscando..." : "Buscar"}
        </button>
        {(search || category) && (
          <button type="button" className="secondary" onClick={clear}>
            Limpiar
          </button>
        )}
        <span className="filter-count">
          {items.length} factura{items.length === 1 ? "" : "s"}
        </span>
      </form>
      {error ? (
        <div className="notice error">{error}</div>
      ) : loading ? (
        <p className="muted">Cargando facturas...</p>
      ) : items.length === 0 ? (
        <p className="muted">No se encontraron facturas.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Factura</th>
                <th>Solicitud</th>
                <th>Proveedor</th>
                <th>Categoría</th>
                <th>Monto</th>
                <th>Solicitante</th>
                <th>Cierre</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {items.map((x) => (
                <tr key={x.attachment_id}>
                  <td>
                    <strong>{x.original_name}</strong>
                    <span className="subtext">
                      {(x.size / 1024 / 1024).toFixed(2)} MB ·{" "}
                    {approvalTimestamp(x.uploaded_at)}
                    </span>
                  </td>
                  <td>
                    <strong>{x.display_id}</strong>
                    <span className="subtext">{x.title}</span>
                  </td>
                  <td>{x.supplier}</td>
                  <td>
                    {categoryOptions.find(
                      ([code]) => code === x.expense_type,
                    )?.[1] || x.expense_type}
                    <span className="subtext">
                      {subcategoryName(x.expense_subcategory)}
                    </span>
                  </td>
                  <td>
                    $
                    {Number(x.amount).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                  <td>{x.requested_by}</td>
                  <td>
                    {x.closed_at ? approvalTimestamp(x.closed_at) : "—"}
                    <span className="subtext">{x.closed_by || ""}</span>
                  </td>
                  <td>
                    <button
                      className="primary nowrap"
                      onClick={() => download(x)}
                    >
                      Descargar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Users({ canConfigure, canEditPeople, view }) {
  const permissions = [
    ["can_request", "Solicitar"],
    ["can_approve", "Aprobar"],
    ["can_view", "Consultar"],
    ["can_configure", "Configuración"],
  ];
  const blank = {
    identity_document: "",
    first_name: "",
    middle_name: "",
    last_name: "",
    second_last_name: "",
    phone: "",
    email: "",
    title: "",
    active: true,
  };
  const emptyProfile = {
    name: "",
    can_request: false,
    can_approve: false,
    can_view: true,
    can_configure: false,
    has_user_limit: false,
    max_users: null,
    active: true,
  };
  const [form, setForm] = useState(blank),
    [users, setUsers] = useState([]),
    [drafts, setDrafts] = useState({}),
    [apartmentMaster, setApartmentMaster] = useState([]),
    [apartmentDrafts, setApartmentDrafts] = useState({}),
    [apartmentSearch, setApartmentSearch] = useState(""),
    [board, setBoard] = useState({ president_id: "", vice_president_id: "", treasurer_id: "", vocal_ids: [] }),
    [profiles, setProfiles] = useState([]),
    [profileDrafts, setProfileDrafts] = useState({}),
    [profileForm, setProfileForm] = useState(emptyProfile),
    [message, setMessage] = useState(null),
    [saving, setSaving] = useState(null),
    [userSearch, setUserSearch] = useState(""),
    [personSearch, setPersonSearch] = useState(""),
    [personResults, setPersonResults] = useState([]),
    [editingUserId, setEditingUserId] = useState(null);
  const draftFor = (u) => ({
    title: u.title,
    active: u.active,
  });
  const apartmentDraftFor = (apartment) => ({
    owner_identity_document: apartment.residents.find((item) => item.ownership_role === "OWNER")?.identity_document || "",
    co_owner_identity_document: apartment.residents.find((item) => item.ownership_role === "CO_OWNER")?.identity_document || "",
    is_rental: apartment.is_rental,
  });
  const load = async () => {
    try {
      const [userData, profileData] = await Promise.all([
        api("/api/users"),
        api("/api/users/profiles?include_inactive=true"),
      ]);
      setUsers(userData);
      setDrafts(Object.fromEntries(userData.map((u) => [u.id, draftFor(u)])));
      setProfiles(profileData.filter((profile) => allowedAccessTitles.has(profile.code)));
      setBoard({
        president_id: userData.find((u) => u.title === "PRESIDENTE")?.id || "",
        vice_president_id: userData.find((u) => u.title === "VICEPRESIDENTE")?.id || "",
        treasurer_id: userData.find((u) => u.title === "TESORERO")?.id || "",
        vocal_ids: userData.filter((u) => u.title === "VOCERO").map((u) => u.id),
      });
      setProfileDrafts(
        Object.fromEntries(
          profileData.map((p) => [
            p.id,
            {
              name: p.name,
              active: p.active,
              has_user_limit: p.has_user_limit,
              max_users: p.max_users,
              ...Object.fromEntries(
                permissions.map(([key]) => [key, Boolean(p[key])]),
              ),
            },
          ]),
        ),
      );
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
  };
  useEffect(() => {
    load();
  }, []);
  const setTitle = (title, target = "form") => {
    if (target === "form") setForm({ ...form, title });
    else setDrafts({ ...drafts, [target]: { ...drafts[target], title } });
  };
  const savePerson = async (e) => {
    e.preventDefault();
    const wasEditing = Boolean(editingUserId);
    setSaving("person");
    try {
      const payload = { ...form };
      await api(editingUserId ? `/api/users/${editingUserId}` : "/api/users", {
        method: editingUserId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setForm(blank);
      setEditingUserId(null);
      setPersonResults([]);
      setPersonSearch("");
      setMessage({
        type: "success",
        text: wasEditing
          ? "Los datos de la persona fueron actualizados y auditados."
          : form.active
            ? "Usuario registrado con sus permisos iniciales. Se envió una contraseña temporal a su correo."
            : "Usuario registrado como inactivo. No se envió acceso por correo.",
      });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const searchPeople = async (e) => {
    e.preventDefault();
    setMessage(null);
    if (personSearch.trim().length < 2) {
      setMessage({ type: "error", text: "Escribe al menos 2 caracteres para buscar." });
      return;
    }
    setSaving("person-search");
    try {
      const results = await api(`/api/users/search?q=${encodeURIComponent(personSearch.trim())}&limit=10`);
      setPersonResults(results);
      if (!results.length) setMessage({ type: "error", text: "No se encontraron personas." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const editPerson = (user) => {
    setEditingUserId(user.id);
    setForm({
      identity_document: user.identity_document || "",
      first_name: user.first_name || "",
      middle_name: user.middle_name || "",
      last_name: user.last_name || "",
      second_last_name: user.second_last_name || "",
      phone: user.phone || "",
      email: user.email || "",
      title: user.title || "",
      active: user.active,
    });
    setPersonResults([]);
    setMessage(null);
  };
  const cancelPersonEdit = () => {
    setEditingUserId(null);
    setForm(blank);
    setMessage(null);
  };
  const changedUsers = () => users.filter(dirty);
  const changesFor = (user) => {
    const draft = drafts[user.id];
    if (!draft) return {};
    return Object.fromEntries(
      ["title", "active"]
        .filter((key) => draft[key] !== user[key])
        .map((key) => [key, draft[key]]),
    );
  };
  const saveUsers = async () => {
    const changed = changedUsers();
    if (!changed.length) return;
    setSaving("users");
    try {
      await api("/api/users/bulk", {
        method: "PATCH",
        body: JSON.stringify({
          users: changed.map((u) => ({ id: u.id, ...changesFor(u) })),
        }),
      });
      setMessage({
        type: "success",
        text: `${changed.length} usuario(s) guardado(s) y auditado(s).`,
      });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const regeneratePassword = async (user) => {
    if (
      !window.confirm(
        `¿Regenerar la contraseña de ${user.name}? La contraseña anterior dejará de funcionar y se enviará una nueva por correo.`,
      )
    )
      return;
    setSaving(`password-${user.id}`);
    setMessage(null);
    try {
      await api(`/api/users/${user.id}/regenerate-password`, {
        method: "POST",
      });
      setMessage({
        type: "success",
        text: `Se envió una nueva contraseña temporal a ${user.email}.`,
      });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const changedApartments = () => apartmentMaster.filter((item) =>
    JSON.stringify(apartmentDrafts[item.apartment_number]) !== JSON.stringify(apartmentDraftFor(item)),
  );
  const updateApartmentDraft = (apartmentNumber, changes) => setApartmentDrafts({
    ...apartmentDrafts,
    [apartmentNumber]: { ...apartmentDrafts[apartmentNumber], ...changes },
  });
  const saveApartments = async () => {
    const changed = changedApartments();
    if (!changed.length) return;
    setSaving("apartments");
    setMessage(null);
    try {
      await Promise.all(changed.map((apartment) => api(`/api/users/apartments/${apartment.apartment_number}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...apartmentDrafts[apartment.apartment_number],
          owner_identity_document: apartmentDrafts[apartment.apartment_number].owner_identity_document || null,
          co_owner_identity_document: apartmentDrafts[apartment.apartment_number].co_owner_identity_document || null,
        }),
      })));
      setMessage({ type: "success", text: `${changed.length} apartamento(s) actualizado(s) y auditado(s).` });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const saveBoard = async () => {
    setSaving("board");
    try {
      await api("/api/users/board", {
        method: "PATCH",
        body: JSON.stringify({
          president_id: Number(board.president_id) || null,
          vice_president_id: Number(board.vice_president_id) || null,
          treasurer_id: Number(board.treasurer_id) || null,
          vocal_ids: board.vocal_ids.map(Number),
        }),
      });
      setMessage({ type: "success", text: "Organigrama actualizado." });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const createProfile = async (e) => {
    e.preventDefault();
    try {
      await api("/api/users/profiles", {
        method: "POST",
        body: JSON.stringify(profileForm),
      });
      setProfileForm(emptyProfile);
      setMessage({ type: "success", text: "Cargo creado." });
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  const saveProfile = async (profile) => {
    setSaving(`profile-${profile.id}`);
    try {
      await api(`/api/users/profiles/${profile.id}`, {
        method: "PATCH",
        body: JSON.stringify(profileDrafts[profile.id]),
      });
      setMessage({ type: "success", text: `Cargo ${profile.name} guardado.` });
      await load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(null);
    }
  };
  const profileDirty = (p) => {
    const d = profileDrafts[p.id];
    return (
      d &&
      [
        "name",
        "active",
        "has_user_limit",
        "max_users",
        ...permissions.map(([key]) => key),
      ].some((key) => d[key] !== p[key])
    );
  };
  const dirty = (user) => {
    return Object.keys(changesFor(user)).length > 0;
  };
  const assignedCount = (code) =>
    users.filter((u) => u.active && u.title === code).length;
  const profileIsFull = (profile) =>
    profile.has_user_limit && assignedCount(profile.code) >= profile.max_users;
  const selectedRegistrationProfile = profiles.find((profile) => profile.code === form.title);
  const normalizedUserSearch = userSearch.trim().toLowerCase();
  const visibleUsers = normalizedUserSearch
    ? users.filter((u) =>
        [u.full_name || u.name, u.first_name, u.middle_name, u.last_name, u.second_last_name, u.identity_document, u.email, u.role === "ADMIN" ? "administración" : ""]
          .some((value) => String(value || "").toLowerCase().includes(normalizedUserSearch)),
      )
    : users;
  const editingPerson = editingUserId ? users.find((item) => item.id === editingUserId) : null;
  const personFormDirty = editingPerson
    ? ["identity_document", "first_name", "middle_name", "last_name", "second_last_name", "phone", "email", "title", "active"].some((key) => String(form[key] ?? "") !== String(editingPerson[key] ?? ""))
    : ["identity_document", "first_name", "middle_name", "last_name", "second_last_name", "phone", "email", "title"].some((key) => String(form[key] || "").trim());
  const usersHavePendingChanges = view === "people"
    ? personFormDirty
    : view === "apartments"
      ? changedApartments().length > 0
      : changedUsers().length > 0 || profiles.some(profileDirty) || Object.keys(emptyProfile).some((key) => profileForm[key] !== emptyProfile[key]);
  return (
    <>
      <span hidden data-unsaved={usersHavePendingChanges ? "true" : "false"} />
      {view === "people" && canEditPeople && (
      <section className="card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">CONFIGURACIÓN DE ACCESOS</p>
            <h2>Crear o modificar usuario</h2>
          </div>
        </div>
        <p className="muted">Los únicos datos personales obligatorios son cédula, primer nombre, primer apellido y correo. Selecciona además el cargo para aplicar sus permisos iniciales.</p>
        <form className="table-filters" onSubmit={searchPeople}>
          <label>
            Buscar persona para modificar
            <input value={personSearch} onChange={(e) => setPersonSearch(e.target.value)} placeholder="Cédula, nombre o correo electrónico..." />
          </label>
          <button className="secondary" disabled={saving === "person-search"}>{saving === "person-search" ? "Buscando..." : "Buscar"}</button>
        </form>
        {personResults.length > 0 && <div className="table-wrap"><table><thead><tr><th>Nombre completo</th><th>Identificación</th><th>Acción</th></tr></thead><tbody>
          {personResults.map((user) => <tr key={user.id}><td>{user.full_name || user.name}</td><td>{user.identity_document}</td><td><button type="button" className="secondary" onClick={() => editPerson(user)}>Modificar</button></td></tr>)}
        </tbody></table></div>}
        {editingUserId && <div className="notice success">Editando una persona existente. La cédula y el correo se validarán antes de guardar.</div>}
        <form className="form-grid" onSubmit={savePerson}>
          <label>
            Cédula o pasaporte
            <input value={form.identity_document} onChange={(e) => setForm({ ...form, identity_document: e.target.value })} required maxLength="50" />
          </label>
          <label>
            Primer nombre
            <input
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              required
            />
          </label>
          <label>
            Segundo nombre
            <input value={form.middle_name} onChange={(e) => setForm({ ...form, middle_name: e.target.value })} />
          </label>
          <label>
            Primer apellido
            <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required />
          </label>
          <label>
            Segundo apellido
            <input value={form.second_last_name} onChange={(e) => setForm({ ...form, second_last_name: e.target.value })} />
          </label>
          <label>
            Correo
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </label>
          <label>
            Teléfono
            <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} maxLength="30" placeholder="Opcional" />
          </label>
          <label>
            Cargo y permisos iniciales
            <select value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required>
              <option value="">Selecciona un cargo</option>
              {profiles.filter((profile) => profile.active || profile.code === form.title).map((profile) => (
                <option key={profile.code} value={profile.code} disabled={!editingUserId && profileIsFull(profile)}>
                  {profile.name}{profile.has_user_limit ? ` · ${assignedCount(profile.code)}/${profile.max_users}` : ""}
                </option>
              ))}
            </select>
          </label>
          {selectedRegistrationProfile && <div className="full permission-summary" aria-label="Permisos del cargo seleccionado">
            {permissions.map(([key, label]) => <span key={key} className={selectedRegistrationProfile[key] ? "granted" : "denied"}>{label}</span>)}
          </div>}
          <label>
            Estado
            <select value={form.active ? "true" : "false"} onChange={(e) => setForm({ ...form, active: e.target.value === "true" })}>
              <option value="true">Activo</option>
              <option value="false">Inactivo</option>
            </select>
          </label>
          <div className="full form-actions">
            {message && (
              <div className={`notice ${message.type}`}>{message.text}</div>
            )}
            {editingUserId && <button type="button" className="secondary" onClick={cancelPersonEdit}>Cancelar modificación</button>}
            <button className="primary" disabled={saving === "person"}>{saving === "person" ? "Guardando..." : editingUserId ? "Guardar modificación" : form.active ? "Registrar y enviar acceso" : "Registrar usuario inactivo"}</button>
          </div>
        </form>
      </section>
      )}
      {view === "apartments" && (
      <section className="card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">MAESTRO DE APARTAMENTOS</p>
            <h2>Propietarios y alquileres</h2>
          </div>
          <div className="bulk-save">
            <span>{changedApartments().length} cambio(s) pendiente(s)</span>
            <button className="primary" disabled={!canEditPeople || !changedApartments().length || saving === "apartments"} onClick={saveApartments}>
              {saving === "apartments" ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </div>
        {message && <div className={`notice ${message.type}`}>{message.text}</div>}
        <div className="table-filters">
          <label>
            Buscar apartamento o propietario
            <input value={apartmentSearch} onChange={(e) => setApartmentSearch(e.target.value)} placeholder="Ej. 21H o apellido..." />
          </label>
          <span className="filter-count">{apartmentMaster.length} apartamento(s)</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Apartamento</th><th>Propietario(s)</th><th>Co-propietario(s)</th><th>Alquiler</th></tr></thead>
            <tbody>
              {apartmentMaster.filter((apartment) => {
                const term = apartmentSearch.trim().toLowerCase();
                return !term || apartment.apartment_number.toLowerCase().includes(term) || apartment.residents.some((resident) => resident.full_name.toLowerCase().includes(term));
              }).map((apartment) => {
                const apartmentDraft = apartmentDrafts[apartment.apartment_number] || apartmentDraftFor(apartment);
                const apartmentDirty = JSON.stringify(apartmentDraft) !== JSON.stringify(apartmentDraftFor(apartment));
                return (
                <tr key={apartment.apartment_number} className={apartmentDirty ? "row-dirty" : ""}>
                  <td><strong>{apartment.apartment_number}</strong></td>
                  {[["OWNER", "Propietario"], ["CO_OWNER", "Co-propietario"]].map(([role, label]) => (
                    <td key={role}>
                      <select aria-label={`${label} de ${apartment.apartment_number}`} value={role === "OWNER" ? apartmentDraft.owner_identity_document : apartmentDraft.co_owner_identity_document} disabled={!canEditPeople || saving === "apartments"} onChange={(e) => updateApartmentDraft(apartment.apartment_number, { [role === "OWNER" ? "owner_identity_document" : "co_owner_identity_document"]: e.target.value })}>
                        <option value="">Sin asignar</option>
                        {users.filter((user) => user.active && ["OWNER", "CO_OWNER"].includes(user.person_type)).map((user) => <option key={user.identity_document} value={user.identity_document}>{user.full_name || user.name} · {user.identity_document}</option>)}
                      </select>
                    </td>
                  ))}
                  <td><button className="secondary" disabled={!canEditPeople || saving === "apartments"} onClick={() => updateApartmentDraft(apartment.apartment_number, { is_rental: !apartmentDraft.is_rental })}>{apartmentDraft.is_rental ? "Sí" : "No"}</button></td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      </section>
      )}
      {view === "organization" && (
      <section className="card">
        <div className="card-heading">
          <div><p className="eyebrow">ESTRUCTURA ORGANIZACIONAL</p><h2>Organigrama</h2></div>
        </div>
        <p className="muted">Solo se muestran las personas con acceso al sistema: Junta Directiva y Administradora.</p>
        <div className="table-wrap"><table><thead><tr><th>Nombre completo</th><th>Cargo</th><th>Estado</th></tr></thead><tbody>
          {users.filter((u) => u.role === "ADMIN" || u.title !== "PROPIETARIO").map((u) => {
            const profile = profiles.find((p) => p.code === u.title);
            return <tr key={u.id}><td>{u.full_name || u.name}</td><td>{profile?.name || titleName(u.title)}</td><td>{u.active ? "Activo" : "Inactivo"}</td></tr>;
          })}
        </tbody></table></div>
      </section>
      )}
      {view === "people" && !canEditPeople && (
      <section className="card">
        <div className="card-heading"><div><p className="eyebrow">SOLO LECTURA</p><h2>Usuarios con acceso</h2></div></div>
        <div className="table-wrap"><table><thead><tr><th>Nombre completo</th><th>Identificación</th><th>Correo</th><th>Cargo</th><th>Estado</th></tr></thead><tbody>
          {users.map((u) => <tr key={u.id}><td>{u.full_name || u.name}</td><td>{u.identity_document || "—"}</td><td>{u.email}</td><td>{profiles.find((p) => p.code === u.title)?.name || titleName(u.title)}</td><td>{u.active ? "Activo" : "Inactivo"}</td></tr>)}
        </tbody></table></div>
      </section>
      )}
      {view === "organization" && <>
      <section className="card">
        <div className="card-heading">
          <div>
            <h2>Asignación de cargos</h2>
            <p className="muted">
              Los permisos se administran en Perfiles de acceso y se aplican mediante el cargo asignado.
            </p>
          </div>
          <div className="bulk-save">
            <span>{changedUsers().length} cambio(s) pendiente(s)</span>
            <button
              className="primary"
              disabled={!canConfigure || !changedUsers().length || saving === "users"}
              onClick={saveUsers}
            >
              {saving === "users" ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </div>
        <div className="table-filters">
          <label>
            Buscar usuario
            <input
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Nombre, correo o apartamento..."
            />
          </label>
          {userSearch && (
            <button className="secondary" onClick={() => setUserSearch("")}>
              Limpiar
            </button>
          )}
          <span className="filter-count">
            {normalizedUserSearch
              ? `${visibleUsers.length} resultado(s)`
              : `${visibleUsers.length} usuario(s) con acceso`}
          </span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Cargo</th>
                <th>Fecha de registro</th>
                <th>Actualización</th>
                <th>Estado</th>
                <th>Seguridad</th>
              </tr>
            </thead>
            <tbody>
              {visibleUsers.map((u) => {
                const d = drafts[u.id] || u,
                  isSystemAdmin = u.role === "ADMIN";
                return (
                  <tr key={u.id} className={dirty(u) ? "row-dirty" : ""}>
                    <td>
                      <strong>{u.full_name || u.name}</strong>
                      <span className="subtext">{u.email}</span>
                      {u.identity_document && <span className="subtext">ID: {u.identity_document} · Tel: {u.phone || "—"}</span>}
                      {u.must_change_password && (
                        <span className="subtext">Cambio de contraseña pendiente</span>
                      )}
                    </td>
                    <td>
                      {isSystemAdmin ? (
                        <strong>{titleName(u.title)}</strong>
                      ) : (
                        <select
                          disabled={!canConfigure}
                          value={d.title}
                          onChange={(e) => setTitle(e.target.value, u.id)}
                        >
                          {d.title === "SIN_ASIGNAR" && <option value="SIN_ASIGNAR">Sin cargo asignado</option>}
                          {profiles
                            .filter((p) => p.active || p.code === d.title)
                            .map((p) => {
                              const fullForOther =
                                profileIsFull(p) && u.title !== p.code;
                              return (
                                <option
                                  key={p.code}
                                  value={p.code}
                                  disabled={fullForOther}
                                >
                                  {p.name}
                                  {p.has_user_limit
                                    ? ` · ${assignedCount(p.code)}/${p.max_users}`
                                    : ""}
                                </option>
                              );
                            })}
                        </select>
                      )}
                    </td>
                    <td>{panamaDate(u.created_at)}</td>
                    <td>{panamaDate(u.updated_at)}</td>
                    <td>
                      <button
                        className="secondary"
                        disabled={!canConfigure || isSystemAdmin}
                        onClick={() =>
                          setDrafts({
                            ...drafts,
                            [u.id]: { ...d, active: !d.active },
                          })
                        }
                      >
                        {d.active ? "Activo" : "Inactivo"}
                      </button>
                    </td>
                    <td>
                      <button
                        className="secondary nowrap"
                        disabled={
                          !canConfigure || isSystemAdmin ||
                          !u.active ||
                          saving === `password-${u.id}`
                        }
                        onClick={() => regeneratePassword(u)}
                      >
                        {saving === `password-${u.id}`
                          ? "Enviando..."
                          : "Regenerar contraseña"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card" style={{ display: view === "organization" ? undefined : "none" }}>
        <div className="card-heading">
          <div>
            <p className="eyebrow">CARGOS CONFIGURABLES</p>
            <h2>Perfiles de acceso</h2>
          </div>
        </div>
        {canConfigure && <form className="profile-create" onSubmit={createProfile}>
          <label>
            Nombre del cargo
            <input
              value={profileForm.name}
              onChange={(e) =>
                setProfileForm({ ...profileForm, name: e.target.value })
              }
              placeholder="Ej. Secretario"
              required
            />
          </label>
          <fieldset className="permission-picker">
            <legend>Permisos predeterminados</legend>
            {permissions.map(([key, label]) => (
              <label key={key}>
                <input
                  type="checkbox"
                  checked={profileForm[key]}
                  onChange={(e) =>
                    setProfileForm({ ...profileForm, [key]: e.target.checked })
                  }
                />
                {label}
              </label>
            ))}
          </fieldset>
          <label className="limit-control">
            <span>
              <input
                type="checkbox"
                checked={profileForm.has_user_limit}
                onChange={(e) =>
                  setProfileForm({
                    ...profileForm,
                    has_user_limit: e.target.checked,
                    max_users: e.target.checked ? 1 : null,
                  })
                }
              />{" "}
              Limitar personas
            </span>
            {profileForm.has_user_limit && (
              <input
                type="number"
                min="1"
                max="10000"
                value={profileForm.max_users || 1}
                onChange={(e) =>
                  setProfileForm({
                    ...profileForm,
                    max_users: Number(e.target.value),
                  })
                }
                required
              />
            )}
          </label>
          <button className="primary">Crear cargo</button>
        </form>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Cargo</th>
                {permissions.map((p) => (
                  <th key={p[0]}>{p[1]}</th>
                ))}
                <th>Tiene límite</th>
                <th>Máximo</th>
                <th>Asignados</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {profiles.map((p) => {
                const d = profileDrafts[p.id] || p;
                return (
                  <tr key={p.id} className={profileDirty(p) ? "row-dirty" : ""}>
                    <td>
                      <input
                        disabled={!canConfigure}
                        value={d.name}
                        onChange={(e) =>
                          setProfileDrafts({
                            ...profileDrafts,
                            [p.id]: { ...d, name: e.target.value },
                          })
                        }
                      />
                    </td>
                    {permissions.map(([key]) => (
                      <td key={key}>
                        <input
                          disabled={!canConfigure}
                          className="permission-check"
                          type="checkbox"
                          checked={Boolean(d[key])}
                          onChange={(e) =>
                            setProfileDrafts({
                              ...profileDrafts,
                              [p.id]: { ...d, [key]: e.target.checked },
                            })
                          }
                        />
                      </td>
                    ))}
                    <td>
                      <input
                        disabled={!canConfigure}
                        className="permission-check"
                        type="checkbox"
                        checked={Boolean(d.has_user_limit)}
                        onChange={(e) =>
                          setProfileDrafts({
                            ...profileDrafts,
                            [p.id]: {
                              ...d,
                              has_user_limit: e.target.checked,
                              max_users: e.target.checked
                                ? d.max_users ||
                                  Math.max(1, assignedCount(p.code))
                                : null,
                            },
                          })
                        }
                      />
                    </td>
                    <td>
                      {d.has_user_limit ? (
                        <input
                          disabled={!canConfigure}
                          className="limit-input"
                          type="number"
                          min={Math.max(1, assignedCount(p.code))}
                          max="10000"
                          value={d.max_users || 1}
                          onChange={(e) =>
                            setProfileDrafts({
                              ...profileDrafts,
                              [p.id]: {
                                ...d,
                                max_users: Number(e.target.value),
                              },
                            })
                          }
                        />
                      ) : (
                        <span className="muted">Sin límite</span>
                      )}
                    </td>
                    <td>
                      {assignedCount(p.code)}
                      {d.has_user_limit ? ` / ${d.max_users || 1}` : ""}
                    </td>
                    <td>
                      <button
                        className="secondary"
                        disabled={!canConfigure}
                        onClick={() =>
                          setProfileDrafts({
                            ...profileDrafts,
                            [p.id]: { ...d, active: !d.active },
                          })
                        }
                      >
                        {d.active ? "Activo" : "Inactivo"}
                      </button>
                    </td>
                    <td>
                      <button
                        className="primary"
                        disabled={
                          !canConfigure || !profileDirty(p) || saving === `profile-${p.id}`
                        }
                        onClick={() => saveProfile(p)}
                      >
                        {saving === `profile-${p.id}`
                          ? "Guardando..."
                          : "Guardar"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      </>}
    </>
  );
}

function Audit() {
  const filters = [["ALL", "Todos"], ["FLOW", "Flujos"], ["USER", "Usuarios"], ["PERMISSION", "Permisos"], ["RULE", "Reglas"]];
  const kindNames = { FLOW: "Flujo", USER: "Usuario", PERMISSION: "Permiso", RULE: "Regla" };
  const actionNames = {
    USER_CREATED: "Usuario creado", USER_ACCESS_UPDATED: "Acceso actualizado",
    USER_PASSWORD_REGENERATED: "Contraseña regenerada", PROFILE_PERMISSIONS_APPLIED: "Permisos aplicados",
    PROFILE_CREATED: "Perfil creado", PROFILE_UPDATED: "Perfil actualizado",
    POLICY_CREATED: "Regla creada", POLICY_UPDATED: "Regla actualizada", POLICY_DELETED: "Regla eliminada",
    APPROVAL_CREATED: "Aprobación creada", APPROVAL_ACTIVATED: "Aprobación activada",
    APPROVAL_APPROVED: "Aprobación concedida", APPROVAL_REJECTED: "Aprobación rechazada",
    REVISION_REQUESTED: "Revisión solicitada",
  };
  const [kind, setKind] = useState("ALL"), [events, setEvents] = useState([]),
    [cursor, setCursor] = useState(null), [hasMore, setHasMore] = useState(false),
    [query, setQuery] = useState(""), [appliedQuery, setAppliedQuery] = useState(""),
    [loading, setLoading] = useState(false), [message, setMessage] = useState(null);
  const load = async (append = false) => {
    setLoading(true); setMessage(null);
    try {
      const cursorQuery = append && cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
      const searchQuery = appliedQuery ? `&q=${encodeURIComponent(appliedQuery)}` : "";
      const result = await api(`/api/audit/events?kind=${kind}&limit=50${searchQuery}${cursorQuery}`);
      setEvents((current) => append ? [...current, ...result.items] : result.items);
      setCursor(result.next_cursor); setHasMore(result.has_more);
    }
    catch (err) { setMessage({ type: "error", text: err.message }); }
    finally { setLoading(false); }
  };
  useEffect(() => {
    setCursor(null); load(false);
  }, [kind, appliedQuery]);
  return <section className="card">
    <div className="card-heading"><div><p className="eyebrow">AUDITORÍA</p><h2>Control de cambios</h2></div>
      <button className="secondary" onClick={() => load(false)} disabled={loading}>{loading ? "Actualizando..." : "Actualizar"}</button>
    </div>
    <p className="muted">Historial inmutable de flujos y cambios en usuarios, permisos y reglas de los últimos 45 días.</p>
    <form className="audit-search" onSubmit={(event) => { event.preventDefault(); setAppliedQuery(query.trim()); }}>
      <label>Buscar en auditoría<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Artículo, proveedor, usuario, aprobador, monto..." /></label>
      <button className="primary" disabled={loading}>Buscar</button>
      {(query || appliedQuery) && <button type="button" className="secondary" onClick={() => { setQuery(""); setAppliedQuery(""); }}>Limpiar</button>}
    </form>
    <div className="audit-filters">{filters.map(([value, label]) => <button key={value} className={kind === value ? "primary" : "secondary"} onClick={() => setKind(value)}>{label}</button>)}</div>
    {message && <div className={`notice ${message.type}`}>{message.text}</div>}
    {!loading && events.length === 0 ? <p className="muted">Aún no hay cambios registrados.</p> :
      <div className="table-wrap"><table><thead><tr><th>Fecha y hora</th><th>Tipo</th><th>Elemento</th><th>Acción</th><th>Realizado por</th><th>Campos / detalle</th></tr></thead>
        <tbody>{events.map((event) => <tr key={event.event_id}>
          <td>{approvalTimestamp(event.occurred_at)}</td><td><span className="change-pill">{kindNames[event.kind] || event.kind}</span></td>
          <td>{event.subject}</td><td>{actionNames[event.event_type] || descriptor(event.event_type)}</td><td>{event.actor}</td>
          <td>{(event.changed_fields || []).map((field) => <span className="change-pill" key={field}>{fieldName(field)}</span>)}
            {event.kind === "FLOW" && event.details?.paso ? <span className="subtext">Paso {event.details.paso} · {event.details.estado_anterior ? statusName(event.details.estado_anterior) : "Inicio"} → {statusName(event.details.estado_nuevo)}</span> : null}</td>
        </tr>)}</tbody></table>
        {hasMore && <div className="audit-load-more"><button className="secondary" disabled={loading} onClick={() => load(true)}>{loading ? "Cargando..." : "Cargar 50 eventos más"}</button></div>}
      </div>}
  </section>;
}

function CategorySettings({ onChanged }) {
  const [items, setItems] = useState([]),
    [selectedCategoryId, setSelectedCategoryId] = useState(""),
    [pendingCategoryId, setPendingCategoryId] = useState(""),
    [savingCategorySwitch, setSavingCategorySwitch] = useState(false),
    [category, setCategory] = useState({ name: "" }),
    [subforms, setSubforms] = useState({}),
    [drafts, setDrafts] = useState({}),
    [message, setMessage] = useState(null);
  const selectedCategory = items.find((item) => String(item.id) === String(selectedCategoryId));
  const categoryHasPendingChanges = (item = selectedCategory) => Boolean(category.name.trim()) || Boolean(item && (
    drafts[`category-${item.id}`] !== item.name
    || item.subcategories.some((sub) => drafts[`subcategory-${sub.id}`] !== sub.name)
    || (subforms[item.id]?.name || "").trim()
  ));
  const requestCategoryChange = (nextId) => {
    if (String(nextId) === String(selectedCategoryId)) return;
    if (categoryHasPendingChanges()) setPendingCategoryId(String(nextId));
    else setSelectedCategoryId(String(nextId));
  };
  const discardAndChangeCategory = () => {
    if (selectedCategory) {
      const restored = { ...drafts, [`category-${selectedCategory.id}`]: selectedCategory.name };
      selectedCategory.subcategories.forEach((sub) => { restored[`subcategory-${sub.id}`] = sub.name; });
      setDrafts(restored);
      setSubforms({ ...subforms, [selectedCategory.id]: { name: "" } });
    }
    setCategory({ name: "" });
    setSelectedCategoryId(pendingCategoryId);
    setPendingCategoryId("");
  };
  const saveAndChangeCategory = async () => {
    if (!selectedCategory) return;
    setSavingCategorySwitch(true);
    setMessage(null);
    try {
      const requests = [];
      if (category.name.trim()) requests.push(api("/api/categories", { method: "POST", body: JSON.stringify({ name: category.name.trim() }) }));
      const categoryKey = `category-${selectedCategory.id}`;
      if (drafts[categoryKey] !== selectedCategory.name) requests.push(api(`/api/categories/${selectedCategory.id}`, { method: "PATCH", body: JSON.stringify({ name: drafts[categoryKey] }) }));
      selectedCategory.subcategories.forEach((sub) => {
        const key = `subcategory-${sub.id}`;
        if (drafts[key] !== sub.name) requests.push(api(`/api/categories/subcategories/${sub.id}`, { method: "PATCH", body: JSON.stringify({ name: drafts[key] }) }));
      });
      const newSubcategory = (subforms[selectedCategory.id]?.name || "").trim();
      if (newSubcategory) requests.push(api(`/api/categories/${selectedCategory.id}/subcategories`, { method: "POST", body: JSON.stringify({ name: newSubcategory }) }));
      await Promise.all(requests);
      setCategory({ name: "" });
      setSubforms({ ...subforms, [selectedCategory.id]: { name: "" } });
      const destination = pendingCategoryId;
      setPendingCategoryId("");
      await load(destination);
      onChanged();
      setMessage({ type: "success", text: "Cambios guardados correctamente." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSavingCategorySwitch(false);
    }
  };
  const load = (preferredId = null) =>
    api("/api/categories?include_inactive=true")
      .then((data) => {
        setItems(data);
        setSelectedCategoryId((current) => {
          const requested = preferredId || current;
          return data.some((item) => String(item.id) === String(requested))
            ? String(requested)
            : String(data.find((item) => item.active)?.id || data[0]?.id || "");
        });
        setDrafts(
          Object.fromEntries(
            data.flatMap((item) => [
              [`category-${item.id}`, item.name],
              ...item.subcategories.map((sub) => [
                `subcategory-${sub.id}`,
                sub.name,
              ]),
            ]),
          ),
        );
      })
      .catch((e) => setMessage({ type: "error", text: e.message }));
  useEffect(load, []);
  const create = async (e) => {
    e.preventDefault();
    try {
      const created = await api("/api/categories", {
        method: "POST",
        body: JSON.stringify({ name: category.name }),
      });
      setCategory({ name: "" });
      setMessage({
        type: "success",
        text: "Categoría creada y código generado automáticamente.",
      });
      load(created.id);
      onChanged();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  const addSub = async (categoryId) => {
    const form = subforms[categoryId] || {};
    try {
      await api(`/api/categories/${categoryId}/subcategories`, {
        method: "POST",
        body: JSON.stringify({ name: form.name || "" }),
      });
      setSubforms({ ...subforms, [categoryId]: { name: "" } });
      load();
      onChanged();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  const toggle = async (path, active) => {
    try {
      await api(path, { method: "PATCH", body: JSON.stringify({ active }) });
      load();
      onChanged();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  const rename = async (path, key) => {
    try {
      await api(path, {
        method: "PATCH",
        body: JSON.stringify({ name: drafts[key] }),
      });
      setMessage({ type: "success", text: "Nombre actualizado." });
      load();
      onChanged();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  return (
    <>
      <span hidden data-unsaved={categoryHasPendingChanges() || category.name.trim() ? "true" : "false"} />
      <section className="card">
        <p className="eyebrow">CATÁLOGOS</p>
        <h2>Registrar categoría</h2>
        <p className="muted">
          El código interno se genera automáticamente. Usa solamente letras y
          espacios; se permiten tildes y ñ.
        </p>
        <form className="form-grid" onSubmit={create}>
          <label className="full">
            Nombre de la categoría
            <input
              value={category.name}
              onChange={(e) => setCategory({ name: e.target.value })}
              placeholder="Ej. Áreas verdes"
              required
            />
          </label>
          <div className="full form-actions">
            {message && (
              <div className={`notice ${message.type}`}>{message.text}</div>
            )}
            <button className="primary">Crear categoría</button>
          </div>
        </form>
      </section>
      <section className="card">
        <h2>Categorías y subcategorías</h2>
        <div className="catalog-selector">
          <label>
            Categoría
            <select value={selectedCategoryId} onChange={(e) => requestCategoryChange(e.target.value)}>
              {items.map((item) => <option key={item.id} value={item.id}>{item.name}{item.active ? "" : " (inactiva)"}</option>)}
            </select>
          </label>
          <span className="filter-count">{items.length} categoría(s)</span>
        </div>
        <div className="catalog-single">
          {items.filter((item) => String(item.id) === String(selectedCategoryId)).map((item) => {
            const categoryKey = `category-${item.id}`;
            return (
              <article className={`catalog-card ${item.active ? "" : "catalog-inactive"}`} key={item.id}>
                <div className="catalog-heading">
                  <div>
                    <input
                      value={drafts[categoryKey] || ""}
                      onChange={(e) =>
                        setDrafts({ ...drafts, [categoryKey]: e.target.value })
                      }
                    />
                    <div className="catalog-meta"><span className={`catalog-status ${item.active ? "active" : "inactive"}`}>{item.active ? "Activa" : "Inactiva"}</span></div>
                  </div>
                  <div className="row-actions">
                    <button
                      className="primary"
                      disabled={drafts[categoryKey] === item.name}
                      onClick={() =>
                        rename(`/api/categories/${item.id}`, categoryKey)
                      }
                    >
                      Guardar
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        toggle(`/api/categories/${item.id}`, !item.active)
                      }
                    >
                      {item.active ? "Desactivar" : "Activar"}
                    </button>
                  </div>
                </div>
                <div className="catalog-subs">
                  {item.subcategories.map((sub) => {
                    const subKey = `subcategory-${sub.id}`;
                    return (
                      <div className={sub.active ? "" : "catalog-inactive"} key={sub.id}>
                        <span>
                          <input
                            value={drafts[subKey] || ""}
                            onChange={(e) =>
                              setDrafts({ ...drafts, [subKey]: e.target.value })
                            }
                          />{" "}
                          <small>{sub.active ? "Activa" : "Inactiva"}</small>
                        </span>
                        <div className="row-actions">
                          <button
                            className="link-button"
                            disabled={drafts[subKey] === sub.name}
                            onClick={() =>
                              rename(
                                `/api/categories/subcategories/${sub.id}`,
                                subKey,
                              )
                            }
                          >
                            Guardar
                          </button>
                          <button
                            className="link-button"
                            onClick={() =>
                              toggle(
                                `/api/categories/subcategories/${sub.id}`,
                                !sub.active,
                              )
                            }
                          >
                            {sub.active ? "Desactivar" : "Activar"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="sub-create single-field">
                  <span className="sub-create-label">Nueva subcategoría</span>
                  <input
                    placeholder="Nombre de la subcategoría"
                    value={subforms[item.id]?.name || ""}
                    onChange={(e) =>
                      setSubforms({
                        ...subforms,
                        [item.id]: { name: e.target.value },
                      })
                    }
                  />
                  <button className="primary" onClick={() => addSub(item.id)}>
                    Agregar
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
      {pendingCategoryId && <div className="confirm-overlay" role="dialog" aria-modal="true" aria-labelledby="category-change-title">
        <section className="confirm-dialog">
          <p className="eyebrow">CAMBIOS PENDIENTES</p>
          <h2 id="category-change-title">¿Deseas guardar antes de continuar?</h2>
          <p className="muted">Hay cambios sin guardar en {selectedCategory?.name}. Elige qué hacer antes de cambiar de categoría.</p>
          <div className="form-actions">
            <button className="primary" disabled={savingCategorySwitch} onClick={saveAndChangeCategory}>{savingCategorySwitch ? "Guardando..." : "Guardar y continuar"}</button>
            <button className="danger" disabled={savingCategorySwitch} onClick={discardAndChangeCategory}>Desechar y continuar</button>
            <button className="secondary" disabled={savingCategorySwitch} onClick={() => setPendingCategoryId("")}>Cancelar</button>
          </div>
        </section>
      </div>}
    </>
  );
}

function ApprovalPage({ token, user }) {
  const [data, setData] = useState(null),
    [comment, setComment] = useState(""),
    [message, setMessage] = useState(null);
  const load = () =>
    api(`/api/approvals/${token}`)
      .then(setData)
      .catch((e) => setMessage({ type: "error", text: e.message }));
  useEffect(load, [token]);
  const decide = async (decision) => {
    if (decision === "REVISION_REQUESTED" && comment.trim().length < 3) {
      setMessage({
        type: "error",
        text: "Indica en el comentario qué debe corregir el solicitante.",
      });
      return;
    }
    try {
      await api(`/api/approvals/${token}`, {
        method: "POST",
        body: JSON.stringify({ decision, comment: comment || null }),
      });
      setMessage({
        type: "success",
        text:
          decision === "REVISION_REQUESTED"
            ? "Solicitud devuelta al solicitante para revisión."
            : "Decisión registrada.",
      });
      load();
    } catch (e) {
      setMessage({ type: "error", text: e.message });
    }
  };
  if (!data)
    return (
      <main className="single">
        <section className="card">
          {message ? (
            <div className="notice error">{message.text}</div>
          ) : (
            "Cargando..."
          )}
        </section>
      </main>
    );
  const x = data.expense,
    pending = data.approval_status === "PENDING",
    preferredAction = new URLSearchParams(window.location.search).get("action"),
    resultClass =
      data.approval_status === "REVISION_REQUESTED"
        ? "revision"
        : data.approval_status.toLowerCase(),
    resultIcon =
      data.approval_status === "APPROVED"
        ? "✓"
        : data.approval_status === "REJECTED"
          ? "×"
          : "!",
    resultLabel =
      data.approval_status === "APPROVED"
        ? "APROBADA"
        : data.approval_status === "REJECTED"
          ? "RECHAZADA"
          : "EN REVISIÓN",
    promptLabel =
      preferredAction === "approve"
        ? "APROBAR"
        : preferredAction === "reject"
          ? "RECHAZAR"
          : "ENVIAR A REVISIÓN";
  return (
    <main className="single">
      <section className="card approval-card">
        <p className="eyebrow">APROBACIÓN DE GASTO</p>
        <h1>Solicitud {x.display_id}</h1>
        <p className="muted">Flujo: {x.flow_id}</p>
        {!pending &&
          ["APPROVED", "REJECTED", "REVISION_REQUESTED"].includes(
            data.approval_status,
          ) && (
            <div className={`decision-result ${resultClass}`}>
              <div className="decision-icon">{resultIcon}</div>
              <strong>{resultLabel}</strong>
              <span>
                {data.approval_status === "REVISION_REQUESTED"
                  ? "La solicitud volvió al solicitante para que realice las correcciones indicadas."
                  : "La decisión fue registrada correctamente."}
              </span>
            </div>
          )}
        {pending && preferredAction && (
          <div className={`action-prompt ${preferredAction}`}>
            El correo solicitó <strong>{promptLabel}</strong>. Revisa todo el
            detalle y confirma tu decisión abajo.
          </div>
        )}
        <div className="amount">
          $
          {Number(x.amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
          })}
        </div>
        <h2>{x.title}</h2>
        <h3 className="detail-title">Detalle de la solicitud</h3>
        <dl className="details">
          <div>
            <dt>Categoría</dt>
            <dd>{x.expense_type}</dd>
          </div>
          <div>
            <dt>Subcategoría</dt>
            <dd>{subcategoryName(x.expense_subcategory) || "—"}</dd>
          </div>
          <div>
            <dt>Proveedor</dt>
            <dd>{x.supplier}</dd>
          </div>
          <div>
            <dt>Solicitante</dt>
            <dd>{x.requested_by}</dd>
          </div>
          <div>
            <dt>Responsable de esta acción</dt>
            <dd>{user.email}</dd>
          </div>
          <div>
            <dt>Estado del paso</dt>
            <dd>{statusName(data.approval_status)}</dd>
          </div>
        </dl>
        <div className="description-box">
          <strong>Descripción / justificación</strong>
          <p>{x.description}</p>
        </div>
        {(x.item_url || x.attachments.length > 0) && (
          <div className="support-box">
            <strong>Soportes de la solicitud</strong>
            {x.item_url && (
              <a href={x.item_url} target="_blank" rel="noreferrer">
                Abrir producto o servicio
              </a>
            )}
            {x.attachments.map((a) => (
              <button
                className="link-button"
                key={a.id}
                onClick={() =>
                  downloadAttachment(a).catch((e) =>
                    setMessage({ type: "error", text: e.message }),
                  )
                }
              >
                Descargar {a.original_name}
              </button>
            ))}
          </div>
        )}
        <label>
          Comentario de la decisión
          <textarea
            rows="4"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            disabled={!pending}
            placeholder="Para revisión, indica qué debe corregir el solicitante."
          />
        </label>
        {message && (
          <div className={`notice ${message.type}`}>{message.text}</div>
        )}
        <div className="decision-actions">
          <button
            className="danger"
            disabled={!pending}
            onClick={() => decide("REJECTED")}
          >
            {preferredAction === "reject" ? "Confirmar rechazo" : "Rechazar"}
          </button>
          <button
            className="review"
            disabled={!pending}
            onClick={() => decide("REVISION_REQUESTED")}
          >
            {preferredAction === "revision"
              ? "Confirmar envío a revisión"
              : "Enviar a revisión"}
          </button>
          <button
            className="primary"
            disabled={!pending}
            onClick={() => decide("APPROVED")}
          >
            {preferredAction === "approve" ? "Confirmar aprobación" : "Aprobar"}
          </button>
        </div>
      </section>
    </main>
  );
}

function RuleSettings({ categoryOptions }) {
  const blank = {
    name: "",
    expense_type: "ALL",
    min_amount: "0",
    max_amount: "",
    approval_mode: "MAJORITY",
    approver_profile_codes: ["PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "VOCERO"],
    active: true,
  };
  const [items, setItems] = useState([]),
    [profiles, setProfiles] = useState([]),
    [form, setForm] = useState(blank),
    [editing, setEditing] = useState(null),
    [message, setMessage] = useState(null),
    [saving, setSaving] = useState(false);
  const load = () =>
    Promise.all([api("/api/rules/policies"), api("/api/users/profiles")])
      .then(([rules, p]) => {
        setItems(rules);
        setProfiles(p.filter((x) => x.active && x.can_approve));
      })
      .catch((e) => setMessage({ type: "error", text: e.message }));
  useEffect(load, []);
  const edit = (item) => {
    setEditing(item.id);
    setForm({
      ...item,
      min_amount: String(item.min_amount),
      max_amount: item.max_amount === null ? "" : String(item.max_amount),
    });
    setMessage(null);
  };
  const toggleProfile = (code) =>
    setForm({
      ...form,
      approver_profile_codes: form.approver_profile_codes.includes(code)
        ? form.approver_profile_codes.filter((x) => x !== code)
        : [...form.approver_profile_codes, code],
    });
  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const payload = {
        ...form,
        min_amount: Number(form.min_amount),
        max_amount: form.max_amount === "" ? null : Number(form.max_amount),
      };
      await api(
        editing ? `/api/rules/policies/${editing}` : "/api/rules/policies",
        { method: editing ? "PUT" : "POST", body: JSON.stringify(payload) },
      );
      setForm(blank);
      setEditing(null);
      setMessage({ type: "success", text: "Regla de aprobación guardada." });
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };
  const remove = async (item) => {
    if (!window.confirm(`¿Eliminar la regla "${item.name}"?`)) return;
    try {
      await api(`/api/rules/policies/${item.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };
  const categoryName = (code) =>
    code === "ALL"
      ? "Todas las categorías"
      : categoryOptions.find((x) => x[0] === code)?.[1] || code;
  const ruleBaseline = editing ? items.find((item) => item.id === editing) : blank;
  const normalizedRule = (value) => JSON.stringify({
    name: value?.name || "", expense_type: value?.expense_type || "ALL",
    min_amount: String(value?.min_amount ?? "0"), max_amount: value?.max_amount == null ? "" : String(value.max_amount),
    approval_mode: "MAJORITY",
    approver_profile_codes: [...(value?.approver_profile_codes || [])].sort(), active: value?.active ?? true,
  });
  const ruleHasPendingChanges = normalizedRule(form) !== normalizedRule(ruleBaseline);
  return (
    <>
      <span hidden data-unsaved={ruleHasPendingChanges ? "true" : "false"} />
      <section className="card rules-form-card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">FLUJOS DE APROBACIÓN</p>
            <h2>{editing ? "Editar regla" : "Nueva regla por rango"}</h2>
            <p className="muted">
              Define el rango, los cargos participantes y si basta una
              aprobación o deben aprobar todos. Los límites son inclusivos.
            </p>
          </div>
        </div>
        <form className="form-grid" onSubmit={save}>
          <label>
            Nombre
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ej. Compras menores"
              required
            />
          </label>
          <label>
            Categoría
            <select
              value={form.expense_type}
              onChange={(e) =>
                setForm({ ...form, expense_type: e.target.value })
              }
            >
              <option value="ALL">Todas las categorías</option>
              {categoryOptions.map(([v, n]) => (
                <option key={v} value={v}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label>
            Monto mínimo (USD)
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.min_amount}
              onChange={(e) => setForm({ ...form, min_amount: e.target.value })}
              required
            />
          </label>
          <label>
            Monto máximo (USD)
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.max_amount}
              onChange={(e) => setForm({ ...form, max_amount: e.target.value })}
              placeholder="Sin límite"
            />
          </label>
          <label className="full">
            Tipo de aprobación
            <select value="MAJORITY" disabled>
              <option value="MAJORITY">Mayoría absoluta — más del 50 %</option>
            </select>
          </label>
          <fieldset className="full rule-profiles">
            <legend>Cargos aprobadores</legend>
            {profiles.map((p) => (
              <label key={p.code}>
                <input
                  type="checkbox"
                  checked={form.approver_profile_codes.includes(p.code)}
                  onChange={() => toggleProfile(p.code)}
                />
                <span>{p.name}</span>
              </label>
            ))}
          </fieldset>
          <label className="active-check">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />{" "}
            Regla activa
          </label>
          <div className="full form-actions">
            {message && (
              <div className={`notice ${message.type}`}>{message.text}</div>
            )}
            {editing && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setEditing(null);
                  setForm(blank);
                }}
              >
                Cancelar
              </button>
            )}
            <button
              className="primary"
              disabled={saving || !form.approver_profile_codes.length}
            >
              {saving ? "Guardando..." : "Guardar regla"}
            </button>
          </div>
        </form>
      </section>
      <section className="card rules-list-card">
        <h2>Reglas configuradas</h2>
        {!items.length ? (
          <p className="muted">
            Aún no hay reglas nuevas. Mientras tanto se mantienen los flujos
            existentes.
          </p>
        ) : (
          <div className="table-wrap rules-table-wrap">
            <table className="rules-table">
              <thead>
                <tr>
                  <th>Regla</th>
                  <th>Categoría</th>
                  <th>Rango</th>
                  <th>Aprobación</th>
                  <th>Cargos</th>
                  <th>Estado</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {items.map((x) => (
                  <tr key={x.id}>
                    <td>
                      <strong>{x.name}</strong>
                    </td>
                    <td>{categoryName(x.expense_type)}</td>
                    <td>
                      ${Number(x.min_amount).toFixed(2)} –{" "}
                      {x.max_amount === null
                        ? "Sin límite"
                        : `$${Number(x.max_amount).toFixed(2)}`}
                    </td>
                    <td>
                      Mayoría absoluta (&gt; 50 %)
                    </td>
                    <td>
                      {x.approver_profile_codes
                        .map(
                          (c) => profiles.find((p) => p.code === c)?.name || c,
                        )
                        .join(", ")}
                    </td>
                    <td>{x.active ? "Activa" : "Inactiva"}</td>
                    <td>
                      <div className="row-actions">
                        <button className="secondary" onClick={() => edit(x)}>
                          Editar
                        </button>
                        <button className="danger" onClick={() => remove(x)}>
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function EmailActionPage({ kind, token }) {
  const endpoint = kind === "approval" ? `/api/approvals/email/${token}` : `/api/expenses/quotation-vote-email/${token}`;
  const [data,setData]=useState(null), [error,setError]=useState(""), [done,setDone]=useState(null), [comment,setComment]=useState("");
  const query = new URLSearchParams(window.location.search);
  const suggested = query.get("action");
  const suggestedOption = Number(query.get("option")) || null;
  useEffect(()=>{ api(endpoint).then(setData).catch((e)=>setError(e.message)); },[endpoint]);
  const submit = async (payload) => { setError(""); try { const result=await api(endpoint,{method:"POST",body:JSON.stringify(payload)}); setDone(result); } catch(e){setError(e.message);} };
  if(done) return <main className="single"><section className="card email-action-card"><p className="eyebrow">RESPUESTA REGISTRADA</p><h1>Gracias por responder</h1><div className="notice success">Tu decisión quedó registrada para {done.display_id}.</div></section></main>;
  if(error) return <main className="single"><section className="card email-action-card"><h1>No se pudo procesar</h1><div className="notice error">{error}</div></section></main>;
  if(!data) return <main className="single">Cargando detalle...</main>;
  const expense=data.expense;
  return <main className="single"><section className="card email-action-card"><p className="eyebrow">CONFIRMACIÓN SEGURA</p><h1>{expense.title}</h1><div className="email-expense-summary"><div><span>Solicitud</span><strong>{expense.display_id}</strong></div><div><span>Urgencia</span><strong>{urgencyName(expense.urgency)}</strong></div>{expense.amount && <div><span>Monto</span><strong>${Number(expense.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</strong></div>}{expense.supplier && <div><span>Proveedor</span><strong>{expense.supplier}</strong></div>}</div><p>{expense.description}</p>
    {kind === "approval" ? <><div className="email-supports"><h2>Cotización y soportes</h2>{expense.item_url && <a className="secondary" href={expense.item_url} target="_blank" rel="noreferrer">Ver cotización en línea</a>}{expense.attachments.map((file)=><a className="secondary" key={file.id} href={apiUrl(`/api/approvals/email/${token}/attachments/${file.id}`)} target="_blank" rel="noreferrer">Ver {file.original_name}</a>)}{!expense.item_url && !expense.attachments.length && <span className="muted">No hay archivos adjuntos.</span>}</div><div className="email-action-buttons"><textarea placeholder="Comentario opcional" value={comment} onChange={(e)=>setComment(e.target.value)}/><button className="primary" onClick={()=>submit({decision:suggested || "APPROVED",comment:comment||null})}>{suggested === "REJECTED" ? "Confirmar rechazo" : suggested === "REVISION_REQUESTED" ? "Confirmar solicitud de corrección" : "Confirmar aprobación"}</button><button className="danger" onClick={()=>submit({decision:"REJECTED",comment:comment||null})}>Rechazar</button></div></>
    : <div className="quotation-audit-list">{expense.options.map((option)=><article className={`quote-option-card ${suggestedOption===option.id?"selected":""}`} key={option.id}><div><strong>Opción {option.option_number}: {option.supplier}</strong><span className="subtext">${Number(option.amount).toLocaleString(undefined,{minimumFractionDigits:2})}</span>{option.notes&&<span className="subtext">{option.notes}</span>}{option.item_url&&<a href={option.item_url} target="_blank" rel="noreferrer">Ver cotización en línea</a>}{option.attachments.map((file)=><a key={file.id} href={apiUrl(`/api/expenses/quotation-vote-email/${token}/attachments/${file.id}`)} target="_blank" rel="noreferrer">📎 Ver {file.original_name}</a>)}</div><button className="primary" onClick={()=>submit({quotation_option_id:option.id})}>{suggestedOption===option.id?"Confirmar este voto":"Votar por esta opción"}</button></article>)}</div>}
  </section></main>;
}

function HomeDashboard({ refreshKey, onOpenRequests }) {
  const [data, setData] = useState(null), [error, setError] = useState("");
  useEffect(() => { api("/api/expenses/dashboard").then(setData).catch((e) => setError(e.message)); }, [refreshKey]);
  if (error) return <section className="card"><div className="notice error">{error}</div></section>;
  if (!data) return <section className="card"><p className="muted">Cargando resumen...</p></section>;
  const month = data.last_31_days;
  return <div className="dashboard-layout">
    <section className="dashboard-kpis">
      <button className="dashboard-kpi attention" onClick={onOpenRequests}><span>Acciones que requieren mi atención</span><strong>{data.pending_my_action}</strong><small>Votos o aprobaciones que esperan tu respuesta</small></button>
      <button className="dashboard-kpi" onClick={onOpenRequests}><span>Solicitudes en proceso</span><strong>{data.in_process}</strong><small>Abiertas actualmente</small></button>
      <article className="dashboard-kpi success"><span>Cerradas en 24 horas</span><strong>{data.closed_last_24h}</strong></article>
    </section>
    <section className="card dashboard-month"><div className="card-heading"><div><p className="eyebrow">ÚLTIMOS 31 DÍAS</p><h2>Resumen de solicitudes</h2></div></div>
      <div className="month-stat-grid"><div><span>Creadas</span><strong>{month.created}</strong></div><div><span>Aprobadas</span><strong>{month.approved}</strong></div><div><span>Cerradas</span><strong>{month.closed}</strong></div><div><span>Rechazadas</span><strong>{month.rejected}</strong></div><div><span>Canceladas</span><strong>{month.cancelled}</strong></div><div><span>Monto aprobado</span><strong>${Number(month.approved_amount).toLocaleString(undefined,{minimumFractionDigits:2})}</strong></div></div>
    </section>
    <section className="card dashboard-pending"><div className="card-heading"><div><p className="eyebrow">REQUIERE TU ATENCIÓN</p><h2>Acciones pendientes</h2></div><button className="secondary" onClick={onOpenRequests}>Ver todas</button></div>
      {data.pending_items.length ? <div className="dashboard-request-list">{data.pending_items.map((item) => <button key={item.request_id} onClick={onOpenRequests}><span><strong>{item.title}</strong><small>{item.display_id} · {statusName(item.status)}</small></span><span className={`urgency-badge urgency-${String(item.urgency).toLowerCase()}`}>{urgencyName(item.urgency)}</span><time>{pendingAge(item.created_at)}</time></button>)}</div> : <p className="muted">No tienes votos ni aprobaciones pendientes.</p>}
    </section>
  </div>;
}

function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [tab, setTab] = useState("home"),
    [configOpen, setConfigOpen] = useState(false),
    [refresh, setRefresh] = useState(0),
    [revision, setRevision] = useState(null),
    [catalog, setCatalog] = useState([]);
  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      setLoading(false);
      return;
    }
    api("/api/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("access_token"))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (user)
      api("/api/categories")
        .then(setCatalog)
        .catch(() => setCatalog([]));
  }, [user, refresh]);
  useEffect(() => {
    if (!user) return undefined;
    let lastHumanActivity = Date.now();
    let lastSync = 0;
    let syncing = false;

    const expireSession = () => {
      localStorage.removeItem("access_token");
      setUser(null);
    };
    const registerActivity = () => {
      const now = Date.now();
      lastHumanActivity = now;
      if (syncing || now - lastSync < ACTIVITY_SYNC_MS) return;
      syncing = true;
      lastSync = now;
      api("/api/auth/activity", { method: "POST" })
        .then((result) => localStorage.setItem("access_token", result.access_token))
        .catch((error) => {
          if (error.status === 401) expireSession();
        })
        .finally(() => {
          syncing = false;
        });
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") registerActivity();
    };
    const events = ["pointerdown", "keydown", "touchstart", "scroll"];
    events.forEach((event) => window.addEventListener(event, registerActivity, { passive: true }));
    document.addEventListener("visibilitychange", onVisibility);
    const timer = window.setInterval(() => {
      if (Date.now() - lastHumanActivity >= SESSION_IDLE_MS) expireSession();
    }, 15000);

    return () => {
      events.forEach((event) => window.removeEventListener(event, registerActivity));
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(timer);
    };
  }, [user]);
  useEffect(() => {
    const warnBeforeUnload = (event) => {
      if (!hasUnsavedChanges()) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, []);
  const emailActionMatch = window.location.pathname.match(/^\/email-action\/(approval|vote)\/([^/]+)$/);
  if (emailActionMatch) return <EmailActionPage kind={emailActionMatch[1]} token={emailActionMatch[2]} />;
  if (loading) return <main className="single">Cargando...</main>;
  if (!user) return <Login onLogin={setUser} />;
  if (user.must_change_password)
    return <ChangePassword user={user} onChanged={setUser} />;
  const match = window.location.pathname.match(/^\/approve\/([^/]+)$/);
  if (match) return <ApprovalPage token={match[1]} user={user} />;
  const logout = () => {
    if (!confirmDiscardChanges()) return;
    localStorage.removeItem("access_token");
    setUser(null);
  };
  const navigateTo = (nextTab) => {
    if (nextTab === tab || !confirmDiscardChanges()) return;
    setTab(nextTab);
    setConfigOpen(false);
  };
  const startRevision = (item) => {
    setRevision(item);
    setTimeout(
      () =>
        document
          .getElementById("expense-form")
          ?.scrollIntoView({ behavior: "smooth" }),
      0,
    );
  };
  const created = () => {
    setRevision(null);
    setRefresh((x) => x + 1);
  };
  const canCreate = user.role === "ADMIN" || user.can_request,
    canApprove = user.role === "ADMIN" || user.can_approve,
    canView = user.role === "ADMIN" || user.can_view,
    canConfigure = user.role === "ADMIN" || user.can_configure,
    isBoardMember = ["PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "VOCERO"].includes(user.title),
    canEditPeople = user.role === "ADMIN" || user.person_type === "ADMINISTRATOR",
    canManagePeople = canConfigure || canEditPeople || isBoardMember,
    canAccessOrganization = canConfigure || isBoardMember;
  const categoryOptions = catalog.map((x) => [x.code, x.name]);
  const subcategoryOptions = Object.fromEntries(
    catalog.map((x) => [
      x.code,
      x.subcategories.filter((s) => s.active).map((s) => [s.code, s.name]),
    ]),
  );
  const titles = {
    home: "Inicio",
    expenses: "Solicitudes de gasto del PH",
    invoices: "Consulta de facturas",
    people: "Configuración · Usuarios con acceso",
    organization: "Configuración · Organigrama",
    categories: "Categorías y subcategorías",
    rules: "Reglas de aprobación",
    audit: "Configuración · Auditoría",
  };
  return (
    <>
      <header className="topbar">
        <div>
          <div className="brand-mark">PH</div>
          <div>
            <strong>Gestión de Gastos</strong>
            <span>
              {user.name} · {roleName(user.role)}
            </span>
          </div>
        </div>
        <div className="header-actions">
          <button onClick={() => navigateTo("home")}>Inicio</button>
          <button onClick={() => navigateTo("expenses")}>Solicitudes</button>
          {canView && (
            <button onClick={() => navigateTo("invoices")}>Facturas</button>
          )}
          {canConfigure && (
            <button onClick={() => navigateTo("audit")}>Auditoría</button>
          )}
          {canManagePeople && (
            <div className="config-menu">
              <button onClick={() => setConfigOpen((open) => !open)}>Configuración {configOpen ? "▴" : "▾"}</button>
              {configOpen && <div className="config-menu-items">
                <button onClick={() => navigateTo("people")}>Personas</button>
                {canAccessOrganization && <button onClick={() => navigateTo("organization")}>Organigrama</button>}
                {canConfigure && <button onClick={() => navigateTo("categories")}>Categorías</button>}
                {canConfigure && <button onClick={() => navigateTo("rules")}>Reglas</button>}
              </div>}
            </div>
          )}
          <button onClick={logout}>Salir</button>
        </div>
      </header>
      <main className="layout">
        <section className="hero">
          <p className="eyebrow">CONTROL · TRAZABILIDAD · APROBACIÓN</p>
          <h1>{titles[tab]}</h1>
        </section>
        {tab === "home" ? (
          <HomeDashboard refreshKey={refresh} onOpenRequests={() => navigateTo("expenses")} />
        ) : tab === "invoices" && canView ? (
          <Invoices categoryOptions={categoryOptions} />
        ) : ["people", "organization"].includes(tab) && canManagePeople && (tab !== "organization" || canAccessOrganization) ? (
          <Users canConfigure={canConfigure} canEditPeople={canEditPeople} view={tab} />
        ) : tab === "categories" && canConfigure ? (
          <CategorySettings onChanged={() => setRefresh((x) => x + 1)} />
        ) : tab === "rules" && canConfigure ? (
          <RuleSettings categoryOptions={categoryOptions} />
        ) : tab === "audit" && canConfigure ? (
          <Audit />
        ) : (
          <>
            {canCreate && (
              <ExpenseForm
                onCreated={created}
                draft={revision}
                onCancelEdit={() => setRevision(null)}
                categoryOptions={categoryOptions}
                subcategoryOptions={subcategoryOptions}
              />
            )}
            <ExpenseTable
              refreshKey={refresh}
              canEdit={canCreate}
              canApprove={canApprove}
              canClose={user.role === "ADMIN" || user.title === "ADMINISTRADORA"}
              onEdit={startRevision}
              onChanged={() => setRefresh((x) => x + 1)}
              categoryOptions={categoryOptions}
            />
          </>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
      <Analytics beforeSend={protectAnalyticsEvent} />
    </AppErrorBoundary>
  </React.StrictMode>,
);
