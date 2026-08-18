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

function replaceClosureVisibility(source) {
  let next = replaceRequired(
    source,
    '{canClose && x.status === "CLOSED" && x.attachments.some((a) => a.document_type === "INVOICE") && <button',
    '{x.can_close && x.status === "CLOSED" && x.attachments.some((a) => a.document_type === "INVOICE") && <button',
    "closed invoice correction guard",
  );
  next = replaceRequired(
    next,
    '{canClose && x.status === "APPROVED" && (',
    '{x.can_close && x.status === "APPROVED" && (',
    "approved closure guard",
  );
  return next;
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

function replaceResourceActionColumn(source) {
  const anyResourceAction = 'filtered.some((item) => item.can_correct || item.can_cancel || item.can_close || item.can_delegate_close)';
  let next = replaceRequired(
    source,
    '{canEdit && <col className="col-actions" />}',
    `{${anyResourceAction} && <col className="col-actions" />}`,
    "resource action column",
  );
  next = replaceRequired(
    next,
    '{canEdit && <th>Acción</th>}',
    `{${anyResourceAction} && <th>Acción</th>}`,
    "resource action header",
  );
  next = replaceRequired(
    next,
    '{(canEdit || canClose) && (',
    '{(x.can_correct || x.can_cancel || x.can_close || x.can_delegate_close) && (',
    "resource action cell",
  );
  return next;
}

function injectClosureDelegationButton(source) {
  const pattern = /(<div className="row-actions">\s*)(\{x\.can_correct\s*&&\s*<button)/g;
  const matches = [...source.matchAll(pattern)];
  if (matches.length !== 1) {
    throw new Error(
      `Legacy main.jsx closure delegation extraction expected 1 row action anchor, found ${matches.length}`,
    );
  }
  return source.replace(
    pattern,
    '$1{x.can_delegate_close && <ClosureDelegationButton expense={x} api={api} onChanged={onChanged} />}\n                        $2',
  );
}

function replaceConfigurationAccess(source) {
  let next = replaceRequired(
    source,
    'canConfigure = user.role === "ADMIN" || user.can_configure,',
    'isSystemAdmin = user.is_system_account === true,\n    canManageAreas = isSystemAdmin || (user.permission_codes || []).includes("areas:manage"),\n    canConfigure = isSystemAdmin,',
    "system administration capability",
  );
  next = replaceRequired(
    next,
    'canEditPeople = user.role === "ADMIN" || user.person_type === "ADMINISTRATOR",',
    'canEditPeople = isSystemAdmin,',
    "people administration capability",
  );
  next = replaceRequired(
    next,
    'canManagePeople = canConfigure || canEditPeople || isBoardMember,',
    'canManagePeople = isSystemAdmin || canManageAreas,',
    "configuration menu capability",
  );
  next = replaceRequired(
    next,
    'canAccessOrganization = canConfigure || isBoardMember;',
    'canAccessOrganization = isSystemAdmin;',
    "organization capability",
  );
  next = replaceRequired(
    next,
    '{configOpen && <div className="config-menu-items">',
    '{configOpen && <div className="config-menu-items" data-system-admin={isSystemAdmin ? "true" : "false"}>',
    "configuration menu marker",
  );
  next = replaceRequired(
    next,
    '<button onClick={() => navigateTo("people")}>Personas</button>',
    '{isSystemAdmin && <button onClick={() => navigateTo("people")}>Personas</button>}',
    "users menu visibility",
  );
  next = replaceRequired(
    next,
    '{canConfigure && <button onClick={() => navigateTo("categories")}>Categorías</button>}',
    '{canManageAreas && <button onClick={() => navigateTo("categories")}>Categorías</button>}',
    "areas menu visibility",
  );
  next = replaceRequired(
    next,
    'tab === "categories" && canConfigure ?',
    'tab === "categories" && canManageAreas ?',
    "areas page capability",
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
        `${reactImport}\nimport ExpenseForm from "./expense-form.jsx";\nimport HomeDashboard from "./home-dashboard.jsx";\nimport ClosureDelegationButton from "./closure-delegation.jsx";`,
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

      next = replaceResourceActionColumn(next);
      next = replaceCancellationVisibility(next);
      next = replaceCorrectionVisibility(next);
      next = replaceClosureVisibility(next);
      next = injectClosureDelegationButton(next);
      next = replaceCorrectionFormAvailability(next);
      next = replaceConfigurationAccess(next);

      return { code: next, map: null };
    },
  };
}

export default defineConfig({
  plugins: [modularExpenseFormPlugin(), react()],
});
