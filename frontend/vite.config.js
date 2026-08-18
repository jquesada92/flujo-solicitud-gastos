import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function replaceRequired(source, before, after, label) {
  if (!source.includes(before)) {
    throw new Error(`Legacy main.jsx extraction could not find: ${label}`);
  }
  return source.replace(before, after);
}

function replaceCancellationVisibility(source) {
  const pattern = /\{\s*\["SUBMITTED",\s*"PENDING_APPROVAL",\s*"APPROVED"\]\.includes\(\s*x\.status,\s*\)\s*&&\s*\(/g;
  const matches = source.match(pattern) || [];
  if (matches.length !== 1) {
    throw new Error(
      `Legacy main.jsx cancellation extraction expected 1 status guard, found ${matches.length}`,
    );
  }
  return source.replace(pattern, "{x.can_cancel && (");
}

function modularExpenseFormPlugin() {
  return {
    name: "modular-expense-form",
    enforce: "pre",
    transform(code, id) {
      const normalized = id.replaceAll("\\", "/").split("?", 1)[0];
      if (!normalized.endsWith("/src/main.jsx")) return null;

      let next = code;
      const reactImport = `import React, { useEffect, useState } from "react";`;
      next = replaceRequired(
        next,
        reactImport,
        `${reactImport}\nimport ExpenseForm from "./expense-form.jsx";`,
        "React import",
      );

      const formStart = next.indexOf("function ExpenseForm({");
      const formEnd = next.indexOf("function ClosurePanel(", formStart);
      if (formStart < 0 || formEnd < 0 || formEnd <= formStart) {
        throw new Error("Legacy main.jsx extraction could not isolate ExpenseForm");
      }

      // Replace the complete legacy implementation with the imported modular
      // component. Do not patch the JSX mount by exact whitespace/text: the
      // modular component already rehydrates when draft/request/flow changes.
      next = `${next.slice(0, formStart)}${next.slice(formEnd)}`;

      // The legacy table previously inferred cancellation from a fixed status
      // list plus can_request. The backend now returns can_cancel per request,
      // so the UI follows that authoritative capability instead.
      next = replaceCancellationVisibility(next);

      return { code: next, map: null };
    },
  };
}

export default defineConfig({
  plugins: [modularExpenseFormPlugin(), react()],
});
