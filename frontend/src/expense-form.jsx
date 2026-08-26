import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = String(import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE_URL}${path}`;

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
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail)) {
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

const emptyQuoteOptions = () => [
  { supplier: "", amount: "", item_url: "", notes: "", file: null, existing_attachment: false },
  { supplier: "", amount: "", item_url: "", notes: "", file: null, existing_attachment: false },
];

export function resolveRequestType(draft) {
  if (!draft) return null;
  if (draft.request_type === "MULTI_QUOTE") return "MULTI_QUOTE";
  if (draft.status === "QUOTATION_VOTING") return "MULTI_QUOTE";
  if ((draft.quotation_options || []).length >= 2) return "MULTI_QUOTE";
  return "SIMPLE";
}

function restoredQuoteOptions(draft) {
  const attachmentOptionIds = new Set(
    (draft?.attachments || [])
      .filter((attachment) => attachment.quotation_option_id != null)
      .map((attachment) => Number(attachment.quotation_option_id)),
  );
  const options = (draft?.quotation_options || []).map((option) => ({
    id: option.id,
    supplier: option.supplier || "",
    amount: String(option.amount ?? ""),
    item_url: option.item_url || "",
    notes: option.notes || "",
    file: null,
    existing_attachment: attachmentOptionIds.has(Number(option.id)),
  }));
  return options.length >= 2 ? options : emptyQuoteOptions();
}

export default function ExpenseForm({
  onCreated,
  draft,
  onCancelEdit,
  categoryOptions = [],
  subcategoryOptions = {},
}) {
  const inferredDraftType = useMemo(() => resolveRequestType(draft), [draft]);
  const [requestType, setRequestType] = useState("SIMPLE");
  const effectiveRequestType = draft ? inferredDraftType : requestType;
  const firstType = categoryOptions[0]?.[0] || "";
  const firstSub = subcategoryOptions[firstType]?.[0]?.[0] || "";
  const empty = useMemo(
    () => ({
      title: "",
      description: "",
      expense_area: firstType,
      expense_category: firstSub,
      urgency: "NORMAL",
      amount: "",
      supplier: "",
      item_url: "",
    }),
    [firstType, firstSub],
  );

  const [form, setForm] = useState(empty);
  const [quotation, setQuotation] = useState(null);
  const [quoteOptions, setQuoteOptions] = useState(emptyQuoteOptions);
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!draft) {
      setRequestType("SIMPLE");
      setQuoteOptions(emptyQuoteOptions());
      setQuotation(null);
      setMessage(null);
      setForm((current) => ({
        ...current,
        expense_area: current.expense_area || firstType,
        expense_category:
          current.expense_category || subcategoryOptions[firstType]?.[0]?.[0] || "",
      }));
      return;
    }

    const draftType = resolveRequestType(draft);
    setRequestType(draftType);
    setForm({
      title: draft.title || "",
      description: draft.description || "",
      expense_area: draft.expense_area || firstType,
      expense_category: draft.expense_category || "",
      urgency: draft.urgency || "NORMAL",
      amount: draftType === "SIMPLE" ? String(draft.amount ?? "") : "",
      supplier: draftType === "SIMPLE" ? draft.supplier || "" : "",
      item_url: draftType === "SIMPLE" ? draft.item_url || "" : "",
    });
    setQuoteOptions(draftType === "MULTI_QUOTE" ? restoredQuoteOptions(draft) : emptyQuoteOptions());
    setQuotation(null);
    setMessage(null);
  }, [draft?.request_id, draft?.flow_id, firstType]);

  const quoteDirty = effectiveRequestType === "MULTI_QUOTE" && Boolean(
    quoteOptions.some((option, index) => {
      const original = draft?.quotation_options?.[index];
      if (!draft) return [option.supplier, option.amount, option.item_url, option.notes].some((value) => String(value || "").trim()) || Boolean(option.file);
      if (!original) return true;
      return (
        String(option.supplier || "") !== String(original.supplier || "") ||
        String(option.amount || "") !== String(original.amount ?? "") ||
        String(option.item_url || "") !== String(original.item_url || "") ||
        String(option.notes || "") !== String(original.notes || "") ||
        Boolean(option.file)
      );
    }),
  );
  const expenseDirty = Boolean(quotation) || quoteDirty || (draft
    ? ["title", "description", "expense_area", "expense_category", "urgency"].some(
        (key) => String(form[key] || "") !== String(draft[key] || ""),
      ) || (effectiveRequestType === "SIMPLE" && (
        String(form.supplier || "") !== String(draft.supplier || "") ||
        String(form.item_url || "") !== String(draft.item_url || "") ||
        String(form.amount || "") !== String(draft.amount ?? "")
      ))
    : ["title", "description", "amount", "supplier", "item_url"].some(
        (key) => String(form[key] || "").trim(),
      ));

  const hasExistingSimpleSupport = Boolean(
    (draft?.attachments || []).some(
      (attachment) => attachment.quotation_option_id == null && attachment.document_type !== "INVOICE",
    ),
  );

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);

    if (effectiveRequestType === "SIMPLE" && !form.item_url && !quotation && !hasExistingSimpleSupport) {
      setMessage({ type: "error", text: "Debes proporcionar una URL o adjuntar una cotización." });
      setSaving(false);
      return;
    }

    if (
      effectiveRequestType === "MULTI_QUOTE" &&
      quoteOptions.some((option) => !option.item_url && !option.file && !option.existing_attachment)
    ) {
      setMessage({ type: "error", text: "Cada cotización debe incluir una URL o un archivo adjunto." });
      setSaving(false);
      return;
    }

    if (effectiveRequestType === "MULTI_QUOTE") {
      const urls = quoteOptions
        .filter((option) => option.item_url)
        .map((option) => {
          const parsed = new URL(option.item_url.trim());
          parsed.hash = "";
          return parsed.toString().replace(/\/$/, "");
        });
      if (new Set(urls).size !== urls.length) {
        setMessage({ type: "error", text: "Cada opción debe utilizar una URL de cotización diferente." });
        setSaving(false);
        return;
      }
      const fileNames = quoteOptions
        .filter((option) => option.file)
        .map((option) => option.file.name.trim().toLowerCase());
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
        request_type: effectiveRequestType,
        amount: effectiveRequestType === "SIMPLE" ? Number(form.amount) : null,
        supplier: effectiveRequestType === "SIMPLE" ? form.supplier : null,
        item_url: effectiveRequestType === "SIMPLE" ? form.item_url || null : null,
        quotation_pending: effectiveRequestType === "SIMPLE" && Boolean(quotation || hasExistingSimpleSupport),
        quotation_options:
          effectiveRequestType === "MULTI_QUOTE"
            ? quoteOptions.map((option) => ({
                supplier: option.supplier,
                amount: Number(option.amount),
                item_url: option.item_url || null,
                notes: option.notes || null,
                attachment_pending: Boolean(option.file || option.existing_attachment),
              }))
            : [],
      };

      item = await api(
        draft ? `/api/expenses/${draft.internal_request_id || draft.request_id}/resubmit` : "/api/expenses",
        { method: draft ? "PUT" : "POST", body: JSON.stringify(payload) },
      );

      if (effectiveRequestType === "SIMPLE" && quotation) {
        const data = new FormData();
        data.append("file", quotation);
        await api(`/api/expenses/${item.request_id}/attachments`, { method: "POST", body: data });
      }

      if (effectiveRequestType === "MULTI_QUOTE") {
        for (let index = 0; index < quoteOptions.length; index += 1) {
          const file = quoteOptions[index].file;
          if (!file) continue;
          const data = new FormData();
          data.append("file", file);
          await api(
            `/api/expenses/${item.request_id}/quotation-options/${item.quotation_options[index].id}/attachment`,
            { method: "POST", body: data },
          );
        }
      }

      setForm(empty);
      setQuotation(null);
      setQuoteOptions(emptyQuoteOptions());
      setMessage({ type: "success", text: `Solicitud ${item.display_id} enviada nuevamente al flujo.` });
      onCreated?.();
    } catch (err) {
      setMessage({
        type: "error",
        text: item
          ? `No se pudo completar el envío de la solicitud ${item.display_id}: ${err.message}`
          : err.message,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="card" id="expense-form">
      <span hidden data-unsaved={expenseDirty ? "true" : "false"} />
      <div className="card-heading">
        <div>
          <p className="eyebrow">{draft ? "CORRECCIÓN Y REENVÍO" : "NUEVA SOLICITUD"}</p>
          <h2>{draft ? "Corregir solicitud existente" : "Registrar gasto"}</h2>
        </div>
        {draft && (
          <button className="secondary" type="button" onClick={onCancelEdit}>
            Cancelar edición
          </button>
        )}
      </div>

      {draft && (
        <>
          <div className="revision-notice">
            Se actualizará la solicitud <strong>{draft.display_id}</strong> sin crear otra fila. El flujo anterior se invalidará y se generarán enlaces nuevos.
          </div>
          <div className="support-requirement">
            <strong>Tipo de solicitud:</strong>{" "}
            {effectiveRequestType === "MULTI_QUOTE" ? "Múltiples cotizaciones" : "Solicitud sencilla"}. El tipo no cambia durante una corrección.
          </div>
        </>
      )}

      {!draft && (
        <div className="request-type-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={requestType === "SIMPLE"}
            className={requestType === "SIMPLE" ? "active" : ""}
            onClick={() => setRequestType("SIMPLE")}
          >
            Solicitud sencilla
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={requestType === "MULTI_QUOTE"}
            className={requestType === "MULTI_QUOTE" ? "active" : ""}
            onClick={() => setRequestType("MULTI_QUOTE")}
          >
            Múltiples cotizaciones
          </button>
        </div>
      )}

      <form onSubmit={submit} className="form-grid">
        <label className="full">
          Título
          <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required minLength="3" />
        </label>

        <label>
          Área
          <select
            value={form.expense_area}
            onChange={(event) => {
              const area = event.target.value;
              setForm({
                ...form,
                expense_area: area,
                expense_category: subcategoryOptions[area]?.[0]?.[0] || "",
              });
            }}
          >
            {categoryOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>

        <label>
          Categoría
          <select
            value={form.expense_category}
            onChange={(event) => setForm({ ...form, expense_category: event.target.value })}
          >
            {(subcategoryOptions[form.expense_area] || []).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>

        <label>
          Nivel de urgencia
          <select value={form.urgency} onChange={(event) => setForm({ ...form, urgency: event.target.value })}>
            <option value="LOW">Baja</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">Alta</option>
            <option value="CRITICAL">Crítica</option>
          </select>
        </label>

        {effectiveRequestType === "SIMPLE" && (
          <>
            <label>
              Monto (USD)
              <input type="number" min="0.01" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} required />
            </label>
            <label className="full">
              Proveedor
              <input value={form.supplier} onChange={(event) => setForm({ ...form, supplier: event.target.value })} required minLength="2" />
            </label>
            <div className="full support-requirement">Adjunta al menos un soporte para iniciar el flujo: URL, cotización o ambos.</div>
            <label>
              URL del producto o servicio
              <input type="url" value={form.item_url} onChange={(event) => setForm({ ...form, item_url: event.target.value })} placeholder="https://..." />
            </label>
            <label>
              Cotización (PDF o imagen, máx. 10 MB)
              <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(event) => setQuotation(event.target.files[0] || null)} />
            </label>
          </>
        )}

        {effectiveRequestType === "MULTI_QUOTE" && (
          <div className="full quote-options-editor">
            <div className="card-heading">
              <div>
                <h3>Opciones para votación</h3>
                <span className="muted">
                  {draft
                    ? "Edita las cotizaciones existentes. La corrección conserva el tipo y la cantidad de opciones."
                    : "Agrega al menos dos proveedores. Cada opción requiere una URL o un archivo."}
                </span>
              </div>
              {!draft && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    setQuoteOptions([
                      ...quoteOptions,
                      { supplier: "", amount: "", item_url: "", notes: "", file: null, existing_attachment: false },
                    ])
                  }
                >
                  Agregar opción
                </button>
              )}
            </div>

            {quoteOptions.map((option, index) => (
              <fieldset className="quote-option-card" key={option.id || index}>
                <legend>Opción {index + 1}</legend>
                <label>
                  Proveedor
                  <input
                    required
                    minLength="2"
                    value={option.supplier}
                    onChange={(event) =>
                      setQuoteOptions(quoteOptions.map((item, itemIndex) => itemIndex === index ? { ...item, supplier: event.target.value } : item))
                    }
                  />
                </label>
                <label>
                  Monto (USD)
                  <input
                    required
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={option.amount}
                    onChange={(event) =>
                      setQuoteOptions(quoteOptions.map((item, itemIndex) => itemIndex === index ? { ...item, amount: event.target.value } : item))
                    }
                  />
                </label>
                <label>
                  URL de cotización
                  <input
                    type="url"
                    placeholder="https://..."
                    value={option.item_url}
                    onChange={(event) =>
                      setQuoteOptions(quoteOptions.map((item, itemIndex) => itemIndex === index ? { ...item, item_url: event.target.value } : item))
                    }
                  />
                </label>
                <label>
                  Archivo (PDF, PNG, JPG o WEBP)
                  <input
                    type="file"
                    accept="application/pdf,image/jpeg,image/png,image/webp"
                    onChange={(event) =>
                      setQuoteOptions(quoteOptions.map((item, itemIndex) => itemIndex === index ? { ...item, file: event.target.files[0] || null } : item))
                    }
                  />
                  {option.existing_attachment && <span className="subtext">Soporte existente conservado</span>}
                </label>
                <label>
                  Observaciones
                  <input
                    value={option.notes}
                    onChange={(event) =>
                      setQuoteOptions(quoteOptions.map((item, itemIndex) => itemIndex === index ? { ...item, notes: event.target.value } : item))
                    }
                  />
                </label>
                {!draft && quoteOptions.length > 2 && (
                  <button type="button" className="danger-link" onClick={() => setQuoteOptions(quoteOptions.filter((_, itemIndex) => itemIndex !== index))}>
                    Eliminar opción
                  </button>
                )}
              </fieldset>
            ))}
          </div>
        )}

        <label className="full">
          Descripción / justificación
          <textarea rows="4" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} required minLength="3" />
        </label>

        <div className="full form-actions">
          {message && <div className={`notice ${message.type}`}>{message.text}</div>}
          <button className="primary" disabled={saving || !categoryOptions.length || !form.expense_category}>
            {saving ? "Guardando..." : draft ? "Guardar y reenviar" : "Crear solicitud"}
          </button>
        </div>
      </form>
    </section>
  );
}
