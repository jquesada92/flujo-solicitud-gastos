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

function replaceCorrectionVisibility(source) {
  const pattern = /\{canEdit\s*&&\s*x\.status\s*!==\s*"CLOSED"\s*&&\s*<button/g;
  const matches = source.match(pattern) || [];
  if (matches.length !== 1) {
    throw new Error(
      `Legacy main.jsx correction extraction expected 1 correction guard, found ${matches.length}`,
    );
  }
  return source.replace(pattern, "{x.can_correct && <button");
}

function replaceCorrectionFormAvailability(source) {
  const pattern = /\{canCreate\s*&&\s*\(\s*<ExpenseForm/g;
  const matches = source.match(pattern) || [];
  if (matches.length !== 1) {
    throw new Error(
      `Legacy main.jsx correction form extraction expected 1 ExpenseForm guard, found ${matches.length}`,
    );
  }
  return source.replace(pattern, "{(canCreate || revision) && (\n              <ExpenseForm");
}

function replaceCorrectionActionColumn(source) {
  let next = replaceRequired(
    source,
    '{canEdit && <col className="col-actions" />}',
    '{(canEdit || canClose || filtered.some((item) => item.can_correct)) && <col className="col-actions" />}',
    "correction action column",
  );
  next = replaceRequired(
    next,
    '{canEdit && <th>Acción</th>}',
    '{(canEdit || canClose || filtered.some((item) => item.can_correct)) && <th>Acción</th>}',
    "correction action header",
  );
  next = replaceRequired(
    next,
    '{(canEdit || canClose) && (',
    '{(canEdit || canClose || x.can_correct) && (',
    "correction action cell",
  );
  return next;
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
        `${reactImport}\nimport ExpenseForm from "./expense-form.jsx";\nimport HomeDashboard from "./home-dashboard.jsx";`,
        "React import",
      );

      const formStart = next.indexOf("function ExpenseForm({");
      const formEnd = next.indexOf("function ClosurePanel(", formStart);
      if (formStart < 0 || formEnd < 0 || formEnd <= formStart) {
        throw new Error("Legacy main.jsx extraction could not isolate ExpenseForm");
      }

      next = `${next.slice(0, formStart)}${next.slice(formEnd)}`;

      const dashboardStart = next.indexOf("function HomeDashboard({");
      const dashboardEnd = next.indexOf("function App()", dashboardStart);
      if (dashboardStart < 0 || dashboardEnd < 0 || dashboardEnd <= dashboardStart) {
        throw new Error("Legacy main.jsx extraction could not isolate HomeDashboard");
      }

      next = `${next.slice(0, dashboardStart)}${next.slice(dashboardEnd)}`;

      // The table still lives in the legacy monolith. Keep only the resource
      // capability bridge here until ExpenseTable is modularized; dashboard
      // wording/behavior lives directly in home-dashboard.jsx.
      next = replaceCancellationVisibility(next);
      next = replaceCorrectionVisibility(next);
      next = replaceCorrectionFormAvailability(next);
      next = replaceCorrectionActionColumn(next);

      return { code: next, map: null };
    },
  };
}

export default defineConfig({
  plugins: [modularExpenseFormPlugin(), react()],
});
