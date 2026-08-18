import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function replaceRequired(source, before, after, label) {
  if (!source.includes(before)) {
    throw new Error(`Legacy main.jsx extraction could not find: ${label}`);
  }
  return source.replace(before, after);
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
      next = `${next.slice(0, formStart)}${next.slice(formEnd)}`;

      next = replaceRequired(
        next,
        `              <ExpenseForm\n                onCreated={created}`,
        `              <ExpenseForm\n                key={revision ? revision.request_id + ":" + (revision.flow_id || revision.status || "draft") : "new-request"}\n                onCreated={created}`,
        "ExpenseForm mount",
      );

      return { code: next, map: null };
    },
  };
}

export default defineConfig({
  plugins: [modularExpenseFormPlugin(), react()],
});
