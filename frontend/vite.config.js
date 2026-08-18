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

      next = replaceRequired(
        next,
        `  const [requestType, setRequestType] = useState("SIMPLE");`,
        `  const inferredDraftType = draft?.request_type === "MULTI_QUOTE" || (draft?.quotation_options || []).length >= 2 || draft?.status === "QUOTATION_VOTING" ? "MULTI_QUOTE" : "SIMPLE";\n  const [requestType, setRequestType] = useState(inferredDraftType);\n  // Creation uses the selected tab. Correction is authoritative from persisted draft evidence.\n  const effectiveRequestType = draft ? inferredDraftType : requestType;`,
        "authoritative request type derived from draft",
      );

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
      const draftType = draft.request_type === "MULTI_QUOTE" || (draft.quotation_options || []).length >= 2 || draft.status === "QUOTATION_VOTING" ? "MULTI_QUOTE" : "SIMPLE";
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
        `              <ExpenseForm\n                onCreated={created}`,
        `              <ExpenseForm\n                key={revision ? revision.request_id + ":" + (revision.flow_id || revision.status || "draft") : "new-request"}\n                onCreated={created}`,
        "force correction form remount",
      );

      next = replaceRequired(
        next,
        `if (requestType === "SIMPLE" && !form.item_url && !quotation) {`,
        `if (effectiveRequestType === "SIMPLE" && !form.item_url && !quotation && !(draft?.attachments || []).some((attachment) => !attachment.quotation_option_id && attachment.document_type !== "INVOICE")) {`,
        "simple correction support validation uses canonical type",
      );

      next = replaceRequired(
        next,
        `if (requestType === "MULTI_QUOTE" && quoteOptions.some((option) => !option.item_url && !option.file)) {`,
        `if (effectiveRequestType === "MULTI_QUOTE" && quoteOptions.some((option) => !option.item_url && !option.file && !option.existing_attachment)) {`,
        "multi quote validation uses canonical type",
      );

      next = replaceRequired(
        next,
        `if (requestType === "MULTI_QUOTE") {\n      const urls =`,
        `if (effectiveRequestType === "MULTI_QUOTE") {\n      const urls =`,
        "multi quote duplicate-url validation uses canonical type",
      );

      next = replaceRequired(
        next,
        `        request_type: requestType,\n        amount: requestType === "SIMPLE" ? Number(form.amount) : null,\n        supplier: requestType === "SIMPLE" ? form.supplier : null,`,
        `        request_type: effectiveRequestType,\n        amount: effectiveRequestType === "SIMPLE" ? Number(form.amount) : null,\n        supplier: effectiveRequestType === "SIMPLE" ? form.supplier : null,`,
        "payload request type is canonical during correction",
      );

      next = replaceRequired(
        next,
        `        quotation_pending: Boolean(quotation),\n        quotation_options: requestType === "MULTI_QUOTE" ? quoteOptions.map((option) => ({`,
        `        quotation_pending: Boolean(quotation || (draft?.attachments || []).some((attachment) => !attachment.quotation_option_id && attachment.document_type !== "INVOICE")),\n        quotation_options: effectiveRequestType === "MULTI_QUOTE" ? quoteOptions.map((option) => ({`,
        "quotation payload uses canonical type",
      );

      next = replaceRequired(
        next,
        `notes: option.notes || null, attachment_pending: Boolean(option.file),`,
        `notes: option.notes || null, attachment_pending: Boolean(option.file || option.existing_attachment),`,
        "existing multi-quote support payload",
      );

      next = replaceRequired(
        next,
        `      if (requestType === "SIMPLE" && quotation) {`,
        `      if (effectiveRequestType === "SIMPLE" && quotation) {`,
        "simple attachment upload uses canonical type",
      );

      next = replaceRequired(
        next,
        `      if (requestType === "MULTI_QUOTE") {`,
        `      if (effectiveRequestType === "MULTI_QUOTE") {`,
        "multi quote attachment upload uses canonical type",
      );

      next = replaceRequired(
        next,
        `      {!draft && <div className="request-type-tabs" role="tablist">`,
        `      {draft && <div className="full support-requirement"><strong>Tipo de solicitud:</strong> {effectiveRequestType === "MULTI_QUOTE" ? "Múltiples cotizaciones" : "Solicitud sencilla"}. El tipo no cambia durante una corrección.</div>}\n      {!draft && <div className="request-type-tabs" role="tablist">`,
        "show readonly correction request type",
      );

      next = replaceRequired(
        next,
        `{requestType === "SIMPLE" && <label>`,
        `{effectiveRequestType === "SIMPLE" && <label>`,
        "simple amount rendering uses canonical type",
      );

      next = replaceRequired(
        next,
        `{requestType === "SIMPLE" && <label className="full">`,
        `{effectiveRequestType === "SIMPLE" && <label className="full">`,
        "simple supplier rendering uses canonical type",
      );

      next = replaceRequired(
        next,
        `{requestType === "SIMPLE" && <div className="full support-requirement">`,
        `{effectiveRequestType === "SIMPLE" && <div className="full support-requirement">`,
        "simple support notice rendering uses canonical type",
      );

      next = replaceRequired(
        next,
        `{requestType === "SIMPLE" && <label>\n          URL del producto o servicio`,
        `{effectiveRequestType === "SIMPLE" && <label>\n          URL del producto o servicio`,
        "simple URL rendering uses canonical type",
      );

      next = replaceRequired(
        next,
        `{requestType === "SIMPLE" && <label>\n          Cotización (PDF o imagen, máx. 10 MB)`,
        `{effectiveRequestType === "SIMPLE" && <label>\n          Cotización (PDF o imagen, máx. 10 MB)`,
        "simple file rendering uses canonical type",
      );

      next = replaceRequired(
        next,
        `{requestType === "MULTI_QUOTE" && <div className="full quote-options-editor">`,
        `{effectiveRequestType === "MULTI_QUOTE" && <div className="full quote-options-editor">`,
        "multi quote editor rendering uses canonical type",
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
