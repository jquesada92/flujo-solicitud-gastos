import React, { useEffect, useMemo, useRef, useState } from "react";
import "./direct-expense-form.css";

const money = (value) => Number(value).toLocaleString("es-PA", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const amountIsInside = (amount, policy) => {
  const minimum = Number(policy.min_amount);
  const maximum = policy.max_amount == null ? null : Number(policy.max_amount);
  return amount > minimum && (maximum === null || amount <= maximum);
};

const policyBand = (policy) => policy.max_amount == null
  ? `($${money(policy.min_amount)}, sin límite)`
  : `($${money(policy.min_amount)}, $${money(policy.max_amount)}]`;

export function resolveDirectExpensePolicy(policies, expenseArea, amount) {
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return policies.find(
    (policy) => policy.expense_area === expenseArea && amountIsInside(amount, policy),
  ) || policies.find(
    (policy) => policy.expense_area === "ALL" && amountIsInside(amount, policy),
  ) || null;
}

export default function DirectExpenseForm({ api, categoryOptions = [], onCreated }) {
  const firstArea = categoryOptions[0]?.[0] || "";
  const invoiceInput = useRef(null);
  const [form, setForm] = useState({
    expense_area: firstArea,
    supplier: "",
    item_description: "",
    amount: "",
  });
  const [invoice, setInvoice] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [loadingPolicies, setLoadingPolicies] = useState(true);
  const [policyError, setPolicyError] = useState("");
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!firstArea) return;
    setForm((current) => current.expense_area
      ? current
      : { ...current, expense_area: firstArea });
  }, [firstArea]);

  const loadPolicies = ({ fresh = false } = {}) => {
    setLoadingPolicies(true);
    setPolicyError("");
    api("/api/direct-expenses/eligible-policies", fresh ? { cache: "reload" } : {})
      .then((items) => setPolicies(Array.isArray(items) ? items : []))
      .catch((error) => {
        setPolicies([]);
        setPolicyError(error.message);
      })
      .finally(() => setLoadingPolicies(false));
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const areaPolicies = useMemo(() => policies
    .filter((policy) => (
      policy.expense_area === form.expense_area || policy.expense_area === "ALL"
    ))
    .sort((left, right) => {
      const leftFallback = left.expense_area === "ALL" ? 1 : 0;
      const rightFallback = right.expense_area === "ALL" ? 1 : 0;
      return leftFallback - rightFallback || Number(left.min_amount) - Number(right.min_amount);
    }), [policies, form.expense_area]);

  const amountEntered = String(form.amount).trim() !== "";
  const amount = Number(form.amount);
  const matchedPolicy = useMemo(
    () => resolveDirectExpensePolicy(policies, form.expense_area, amount),
    [policies, form.expense_area, amount],
  );
  const dirty = Boolean(
    form.supplier.trim()
    || form.item_description.trim()
    || amountEntered
    || invoice,
  );

  const submit = async (event) => {
    event.preventDefault();
    setMessage(null);

    if (!matchedPolicy) {
      setMessage({
        type: "error",
        text: "El monto no pertenece a una banda activa sin aprobación para esta Área.",
      });
      return;
    }
    if (!invoice) {
      setMessage({ type: "error", text: "Adjunta la factura del gasto." });
      return;
    }

    setSaving(true);
    try {
      const payload = new FormData();
      payload.append("expense_area", form.expense_area);
      payload.append("supplier", form.supplier.trim());
      payload.append("item_description", form.item_description.trim());
      payload.append("amount", form.amount);
      payload.append("invoice", invoice);

      const item = await api("/api/direct-expenses", {
        method: "POST",
        body: payload,
      });

      setForm((current) => ({
        ...current,
        supplier: "",
        item_description: "",
        amount: "",
      }));
      setInvoice(null);
      if (invoiceInput.current) invoiceInput.current.value = "";
      setMessage({
        type: "success",
        text: `Gasto ${item.display_id} registrado con factura. No se creó una solicitud de aprobación.`,
      });
      onCreated?.(item);
    } catch (error) {
      setMessage({ type: "error", text: error.message });
      loadPolicies({ fresh: true });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="direct-expense-layout">
      <span hidden data-unsaved={dirty ? "true" : "false"} />
      <section className="card direct-expense-intro">
        <div>
          <p className="eyebrow">REGISTRO SIN FLUJO</p>
          <h2>Gasto sin aprobación</h2>
          <p className="muted">
            Usa esta pantalla únicamente cuando el Área y el monto pertenezcan a
            una regla activa de “No requiere aprobación”. El registro guarda la
            factura directamente y no crea una solicitud.
          </p>
        </div>
        <div className="direct-expense-assurance" aria-label="Alcance del registro">
          <strong>Sin ronda ni votantes</strong>
          <span>La banda se vuelve a validar en el servidor antes de guardar.</span>
        </div>
      </section>

      <section className="card direct-expense-card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">FACTURA DIRECTA</p>
            <h2>Registrar proveedor, ítem y monto</h2>
          </div>
        </div>

        <form className="form-grid direct-expense-form" onSubmit={submit}>
          <label>
            Área
            <select
              value={form.expense_area}
              onChange={(event) => {
                setForm({ ...form, expense_area: event.target.value });
                setMessage(null);
              }}
              required
              disabled={!categoryOptions.length}
            >
              {categoryOptions.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            Monto (USD)
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={form.amount}
              onChange={(event) => {
                setForm({ ...form, amount: event.target.value });
                setMessage(null);
              }}
              aria-describedby="direct-amount-feedback"
              required
            />
          </label>
          <label>
            Proveedor
            <input
              value={form.supplier}
              onChange={(event) => setForm({ ...form, supplier: event.target.value })}
              minLength="2"
              maxLength="160"
              required
            />
          </label>
          <label>
            Factura (PDF o imagen, máx. 10 MB)
            <input
              ref={invoiceInput}
              type="file"
              accept="application/pdf,image/jpeg,image/png,image/webp"
              onChange={(event) => setInvoice(event.target.files?.[0] || null)}
              required
            />
            {invoice && <span className="direct-file-name">{invoice.name}</span>}
          </label>
          <label className="full">
            Ítem adquirido
            <textarea
              rows="4"
              value={form.item_description}
              onChange={(event) => setForm({ ...form, item_description: event.target.value })}
              minLength="2"
              maxLength="500"
              placeholder="Describe el producto o servicio facturado"
              required
            />
          </label>

          <div className="full direct-policy-panel" id="direct-amount-feedback" aria-live="polite">
            <div className="direct-policy-heading">
              <div>
                <strong>Bandas sin aprobación disponibles</strong>
                <span>El mínimo es excluyente y el máximo es inclusivo.</span>
              </div>
              {policyError && (
                <button type="button" className="secondary" onClick={() => loadPolicies({ fresh: true })}>
                  Reintentar
                </button>
              )}
            </div>

            {loadingPolicies ? (
              <p className="muted">Consultando reglas vigentes…</p>
            ) : policyError ? (
              <div className="notice error">No se pudieron consultar las bandas: {policyError}</div>
            ) : areaPolicies.length ? (
              <div className="direct-band-list">
                {areaPolicies.map((policy) => (
                  <article
                    className={`direct-band ${matchedPolicy?.id === policy.id ? "matched" : ""}`}
                    key={policy.id}
                  >
                    <div>
                      <strong>{policy.name}</strong>
                      <span>{policy.expense_area === "ALL" ? "Respaldo para todas las Áreas" : "Regla específica del Área"}</span>
                    </div>
                    <b>{policyBand(policy)}</b>
                  </article>
                ))}
              </div>
            ) : (
              <div className="direct-policy-empty">
                No hay bandas activas sin aprobación para esta Área ni una regla de respaldo.
              </div>
            )}

            {amountEntered && !loadingPolicies && !policyError && (
              matchedPolicy ? (
                <div className="direct-amount-status eligible">
                  Monto elegible por “{matchedPolicy.name}”. Puedes registrar la factura sin crear una solicitud.
                </div>
              ) : (
                <div className="direct-amount-status ineligible">
                  Este monto requiere el flujo ordinario de Solicitudes porque no coincide con una banda sin aprobación.
                </div>
              )
            )}
          </div>

          <div className="full form-actions direct-expense-actions">
            {message && <div className={`notice ${message.type}`}>{message.text}</div>}
            <button
              className="primary"
              disabled={saving || loadingPolicies || Boolean(policyError) || !matchedPolicy || !form.expense_area}
            >
              {saving ? "Registrando…" : "Registrar gasto y factura"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
