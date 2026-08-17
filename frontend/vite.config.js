import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const DEFAULT_QUOTES = `[
    { supplier: "", amount: "", item_url: "", notes: "", file: null },
    { supplier: "", amount: "", item_url: "", notes: "", file: null },
  ]`;

function replaceRequired(source, before, after, label) {
  if (!source.includes(before)) {
    throw new Error(`Legacy main.jsx revision patch could not find: ${label}`);
  }
  return source.replace(before, after);
}

function legacyRevisionSafetyPlugin() {
  return {
    name: "legacy-revision-safety",
    enforce: "pre",
    transform(code, id) {
      const normalized = id.replaceAll("\\", "/").split("?", 1)[0];
      if (!normalized.endsWith("/src/main.jsx")) return null;

      let next = code;

      const oldDraftState = `    if (draft) {
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
      const expense_type = categoryOptions[0][0];`;

      const newDraftState = `    if (draft) {
      const draftType = draft.request_type === "MULTI_QUOTE" ? "MULTI_QUOTE" : "SIMPLE";
      setRequestType(draftType);
      setForm({
        title: draft.title,
        description: draft.description,
        expense_type: draft.expense_type,
        expense_subcategory: draft.expense_subcategory,
        urgency: draft.urgency || "NORMAL",
        amount: draftType === "SIMPLE" ? String(draft.amount ?? "") : "",
        supplier: draftType === "SIMPLE" ? (draft.supplier || "") : "",
        item_url: draftType === "SIMPLE" ? (draft.item_url || "") : "",
        revised_from_request_id: draft.request_id,
      });
      if (draftType === "MULTI_QUOTE") {
        const attachmentOptionIds = new Set(
          (draft.attachments || [])
            .filter((attachment) => attachment.quotation_option_id != null)
            .map((attachment) => Number(attachment.quotation_option_id)),
        );
        const restoredOptions = (draft.quotation_options || []).map((option) => ({
          id: option.id,
          supplier: option.supplier || "",
          amount: String(option.amount ?? ""),
          item_url: option.item_url || "",
          notes: option.notes || "",
          file: null,
          existing_attachment: attachmentOptionIds.has(Number(option.id)),
        }));
        setQuoteOptions(restoredOptions.length >= 2 ? restoredOptions : ${DEFAULT_QUOTES});
      } else {
        setQuoteOptions(${DEFAULT_QUOTES});
      }
      setQuotation(null);
      setMessage(null);
    } else if (categoryOptions.length) {
      setRequestType("SIMPLE");
      setQuoteOptions(${DEFAULT_QUOTES});
      const expense_type = categoryOptions[0][0];`;

      next = replaceRequired(next, oldDraftState, newDraftState, "draft state restoration");

      next = replaceRequired(
        next,
        `if (requestType === "MULTI_QUOTE" && quoteOptions.some((option) => !option.item_url && !option.file)) {`,
        `if (requestType === "MULTI_QUOTE" && quoteOptions.some((option) => !option.item_url && !option.file && !option.existing_attachment)) {`,
        "existing multi-quote attachment validation",
      );

      next = replaceRequired(
        next,
        `quotation_pending: Boolean(quotation),`,
        `quotation_pending: Boolean(quotation || (draft?.attachments || []).some((attachment) => !attachment.quotation_option_id && attachment.document_type !== "INVOICE")),`,
        "existing simple support validation",
      );

      next = replaceRequired(
        next,
        `notes: option.notes || null, attachment_pending: Boolean(option.file),`,
        `notes: option.notes || null, attachment_pending: Boolean(option.file || option.existing_attachment),`,
        "existing multi-quote support payload",
      );

      next = replaceRequired(
        next,
        `<div className="card-heading"><div><h3>Opciones para votación</h3><span className="muted">Agrega al menos dos proveedores. Cada opción requiere una URL o un archivo.</span></div><button type="button" className="secondary" onClick={() => setQuoteOptions([...quoteOptions, { supplier: "", amount: "", item_url: "", notes: "", file: null }])}>Agregar opción</button></div>`,
        `<div className="card-heading"><div><h3>Opciones para votación</h3><span className="muted">{draft ? "Edita las opciones existentes. La corrección conserva el tipo y la cantidad de cotizaciones." : "Agrega al menos dos proveedores. Cada opción requiere una URL o un archivo."}</span></div>{!draft && <button type="button" className="secondary" onClick={() => setQuoteOptions([...quoteOptions, { supplier: "", amount: "", item_url: "", notes: "", file: null }])}>Agregar opción</button>}</div>`,
        "disable structural quote changes while correcting",
      );

      next = replaceRequired(
        next,
        `{quoteOptions.length > 2 && <button type="button" className="danger-link"`,
        `{!draft && quoteOptions.length > 2 && <button type="button" className="danger-link"`,
        "disable quote removal while correcting",
      );

      return { code: next, map: null };
    },
  };
}

export default defineConfig({
  plugins: [legacyRevisionSafetyPlugin(), react()],
});
