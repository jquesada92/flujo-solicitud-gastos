import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  auditChangeEntries,
  auditChangeTypeName,
  auditValueText,
  defaultAuditDateRange,
} from "../src/audit-utils.js";

const main = readFileSync(new URL("../src/main.jsx", import.meta.url), "utf8");
const mobile = readFileSync(new URL("../src/mobile-layout.css", import.meta.url), "utf8");
const styles = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
const auditStart = main.indexOf("function Audit()");
const auditEnd = main.indexOf("function CategorySettings", auditStart);
const auditSource = main.slice(auditStart, auditEnd);

test("audit actions distinguish creation update and deletion", () => {
  assert.equal(auditChangeTypeName("CREATE"), "Creación");
  assert.equal(auditChangeTypeName("UPDATE"), "Actualización");
  assert.equal(auditChangeTypeName("DELETE"), "Eliminación");
  assert.match(main, /audit-action--\$\{changeTypeClass\}/);
});

test("audit values preserve false zero null arrays and object names", () => {
  assert.equal(auditValueText(false), "No");
  assert.equal(auditValueText(false, "active"), "Inactivo");
  assert.equal(auditValueText(0), "0");
  assert.equal(auditValueText(null), "Sin valor");
  assert.equal(auditValueText([], "assigned_roles"), "Ninguno");
  assert.equal(
    auditValueText([{ id: 1, name: "Solicitante" }, { id: 2, name: "Aprobador" }], "assigned_roles"),
    "Solicitante, Aprobador",
  );
});

test("role changes expose ordered previous and current values", () => {
  const entries = auditChangeEntries({
    changed_fields: ["assigned_roles"],
    changes: {
      assigned_roles: {
        before: [{ id: 1, name: "Rol anterior" }],
        after: [{ id: 2, name: "Rol actual" }],
      },
    },
  });

  assert.deepEqual(entries, [{
    field: "assigned_roles",
    before: [{ id: 1, name: "Rol anterior" }],
    after: [{ id: 2, name: "Rol actual" }],
  }]);
  assert.match(main, /Roles del usuario actualizados/);
  assert.match(main, /Valor anterior/);
  assert.match(main, /Valor actual/);
});

test("audit controls and table expose accessible state", () => {
  assert.match(main, /aria-label="Filtrar auditoría por fecha"/);
  assert.match(main, /type="date" required max=\{dateTo\}/);
  assert.match(main, /type="date" required min=\{dateFrom\}/);
  assert.match(main, /aria-label="Filtrar eventos de auditoría"/);
  assert.match(main, /aria-pressed=\{kind === value\}/);
  assert.match(main, /aria-label="Eventos de auditoría"/);
  assert.match(main, /<time dateTime=\{event\.occurred_at\}>/);
  assert.match(main, /aria-live="polite"/);
});

test("audit defaults to seven Panama calendar dates without a UTC date shift", () => {
  assert.deepEqual(
    defaultAuditDateRange(new Date("2026-09-01T03:30:00Z"), "America/Panama"),
    { dateFrom: "2026-08-25", dateTo: "2026-08-31" },
  );
  assert.deepEqual(
    defaultAuditDateRange(new Date("2026-09-01T05:00:00Z"), "America/Panama"),
    { dateFrom: "2026-08-26", dateTo: "2026-09-01" },
  );
  assert.deepEqual(
    defaultAuditDateRange(new Date("2027-01-02T12:00:00Z"), "America/Panama"),
    { dateFrom: "2026-12-27", dateTo: "2027-01-02" },
  );
});

test("every audit category request preserves the applied date range", () => {
  assert.match(auditSource, /date_from=\$\{encodeURIComponent\(appliedDateFrom\)\}/);
  assert.match(auditSource, /date_to=\$\{encodeURIComponent\(appliedDateTo\)\}/);
  assert.match(auditSource, /\[kind, appliedQuery, appliedDateFrom, appliedDateTo\]/);
  assert.match(auditSource, /resetPagination\(\)/);
  assert.match(main, /Últimos 7 días/);
});

test("audit starts in flows and paginates ten replacement rows without Todos", () => {
  const filterSource = auditSource.match(/const filters = (\[[^\n]+\]);/)?.[1] || "";
  const filterKinds = [...filterSource.matchAll(/\["([A-Z]+)",/g)].map((match) => match[1]);

  assert.deepEqual(filterKinds, ["FLOW", "USER", "PERMISSION", "AREA", "RULE"]);
  assert.doesNotMatch(auditSource, /\bTodos\b/);
  assert.match(auditSource, /const \[kind, setKind\] = useState\("FLOW"\)/);
  assert.match(main, /const AUDIT_PAGE_SIZE = 10;/);
  assert.match(auditSource, /limit=\$\{AUDIT_PAGE_SIZE\}/);
  assert.match(auditSource, /setEvents\(result\.items\);/);
  assert.doesNotMatch(auditSource, /\.\.\.current\s*,\s*\.\.\.result\.items/);
  assert.match(auditSource, /className="audit-pagination" aria-label="Paginaci.n de auditor.a"/);
  assert.match(auditSource, />Anterior<\/button>/);
  assert.match(auditSource, />Siguiente<\/button>/);
  assert.match(styles, /\.audit-pagination\s*\{\s*display:\s*flex;/);
});

test("audit rows become complete cards on narrow screens", () => {
  assert.match(mobile, /\.audit-date-filter input\s*\{[\s\S]*min-height:\s*44px/);
  assert.match(mobile, /\.audit-table tr\s*\{[\s\S]*display:\s*grid/);
  assert.match(mobile, /\.audit-table td::before\s*\{[\s\S]*content:\s*attr\(data-label\)/);
  assert.match(mobile, /\.audit-value-comparison\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\)/);
  assert.match(mobile, /\.audit-pagination\s*\{\s*display:\s*grid;\s*grid-template-columns:\s*minmax\(0, 1fr\) auto minmax\(0, 1fr\)/);
  assert.match(mobile, /\.audit-pagination button\s*\{[\s\S]*min-height:\s*44px/);
});
