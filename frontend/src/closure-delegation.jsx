import React, { useEffect, useState } from "react";

export default function ClosureDelegationButton({ expense, api, onChanged }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const requestId = expense.internal_request_id || expense.request_id;

  const load = async () => {
    setError("");
    try {
      const result = await api(`/api/expenses/${requestId}/closure-delegation`);
      setData(result);
      setSelected(result.delegation?.delegate?.id ? String(result.delegation.delegate.id) : "");
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    if (open) load();
  }, [open, requestId]);

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      const result = await api(`/api/expenses/${requestId}/closure-delegation`, {
        method: "PUT",
        body: JSON.stringify({ delegate_user_id: Number(selected) }),
      });
      setData(result);
      setSelected(result.delegation?.delegate?.id ? String(result.delegation.delegate.id) : "");
      onChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const revoke = async () => {
    setSaving(true);
    setError("");
    try {
      const result = await api(`/api/expenses/${requestId}/closure-delegation`, {
        method: "DELETE",
      });
      setData(result);
      setSelected("");
      onChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button className="secondary nowrap" onClick={() => setOpen(true)}>
        {expense.status === "CLOSED" ? "Delegar factura" : "Delegar cierre/factura"}
      </button>
      {open && (
        <div className="confirm-overlay" role="presentation" onMouseDown={() => setOpen(false)}>
          <section
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="closure-delegation-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="card-heading">
              <div>
                <p className="eyebrow">DELEGACIÓN POR SOLICITUD</p>
                <h2 id="closure-delegation-title">Cierre y factura</h2>
                <span className="muted">{expense.display_id} · {expense.title}</span>
              </div>
              <button className="secondary" onClick={() => setOpen(false)}>Cerrar</button>
            </div>

            <p>
              El solicitante conserva siempre la facultad de registrar/corregir la factura y cerrar.
              Puedes delegar esa responsabilidad a un usuario activo para esta solicitud.
            </p>

            {error && <div className="notice error">{error}</div>}
            {!data ? (
              <p className="muted">Cargando usuarios...</p>
            ) : (
              <>
                {data.delegation && (
                  <div className="notice success">
                    Delegado actual: <strong>{data.delegation.delegate.name}</strong> · {data.delegation.delegate.email}
                  </div>
                )}
                <label>
                  Usuario delegado
                  <select value={selected} onChange={(event) => setSelected(event.target.value)} disabled={saving}>
                    <option value="">Selecciona un usuario</option>
                    {data.candidates.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.name} · {candidate.email}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="row-actions" style={{ marginTop: 16 }}>
                  {data.delegation && (
                    <button className="danger" type="button" disabled={saving} onClick={revoke}>
                      Revocar delegación
                    </button>
                  )}
                  <button className="primary" type="button" disabled={saving || !selected} onClick={save}>
                    {saving ? "Guardando..." : data.delegation ? "Cambiar delegado" : "Delegar"}
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}
