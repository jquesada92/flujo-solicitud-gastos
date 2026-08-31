import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = async (relativePath) => readFile(
  new URL(`../${relativePath}`, import.meta.url),
  "utf8",
);

test("requests:create exposes a dedicated direct-expense screen", async () => {
  const main = await source("src/main.jsx");

  assert.match(main, /import DirectExpenseForm from "\.\/direct-expense-form\.jsx";/);
  const navigation = main.indexOf('onClick={() => navigateTo("direct-expenses")}');
  assert.ok(navigation > 0, "missing direct-expense navigation");
  const navigationGuard = main.lastIndexOf("{canCreate && (", navigation);
  assert.ok(
    navigationGuard > 0 && main.slice(navigationGuard, navigation).includes("<button"),
    "direct-expense navigation must be guarded by requests:create capability",
  );
  assert.match(main, /tab === "direct-expenses" && canCreate/);
  assert.match(main, /<DirectExpenseForm\s+api=\{api\}\s+categoryOptions=\{categoryOptions\}/s);
});

test("NO_APPROVAL request rejection guides users to highlighted direct registration", async () => {
  const [form, main, css] = await Promise.all([
    source("src/expense-form.jsx"),
    source("src/main.jsx"),
    source("src/styles.css"),
  ]);

  assert.match(form, /error\?\.status === 422[\s\S]+includes\(DIRECT_EXPENSE_REQUIRED_PATH\)/);
  assert.match(
    form,
    /El área y el monto seleccionados no requieren un proceso de aprobación\. Usa Registro directo para registrar el gasto y adjuntar la factura\./,
  );
  assert.match(form, /onDirectExpenseSuggestionChange\?\.\(true\)/);
  assert.match(form, /id=\{message\.directExpenseRequired \? "direct-expense-guidance" : undefined\}/);
  assert.match(main, /\[directExpenseSuggested, setDirectExpenseSuggested\] = useState\(false\)/);
  assert.match(main, /aria-describedby=\{directExpenseSuggested \? "direct-expense-guidance" : undefined\}/);
  assert.match(main, /data-attention=\{directExpenseSuggested \? "true" : undefined\}/);
  assert.match(main, /onDirectExpenseSuggestionChange=\{setDirectExpenseSuggested\}/);
  assert.match(main, /querySelector\('\.header-actions button\[data-attention="true"\]'\)[\s\S]+scrollIntoView\(\{ block: "nearest", inline: "center" \}\)/);
  assert.match(css, /\.header-actions button\[data-attention="true"\][\s\S]+background: #fbbf24;/);
});

test("direct expense uses the isolated multipart API and never creates an Expense", async () => {
  const form = await source("src/direct-expense-form.jsx");

  assert.match(form, /api\("\/api\/direct-expenses\/eligible-policies"/);
  assert.match(form, /api\("\/api\/direct-expenses", \{\s*method: "POST",\s*body: payload/s);
  for (const field of ["expense_area", "supplier", "item_description", "amount", "invoice"]) {
    assert.ok(form.includes(`payload.append("${field}"`), `missing multipart field ${field}`);
  }
  assert.doesNotMatch(form, /api\("\/api\/expenses"/);
  assert.match(form, /policy\.expense_area === expenseArea[\s\S]+policy\.expense_area === "ALL"/);
  assert.match(form, /amount > minimum && \(maximum === null \|\| amount <= maximum\)/);
  assert.match(form, /No se creó una solicitud de aprobación/);
});

test("NO_APPROVAL keeps range validation but removes approver targets", async () => {
  const main = await source("src/main.jsx");

  assert.match(main, /<option value="NO_APPROVAL">No requiere aprobación/);
  assert.match(main, /const requiresApprovalTargets = form\.approval_mode !== "NO_APPROVAL"/);
  assert.match(main, /approver_role_ids: requiresApprovalTargets \? form\.approver_role_ids : \[\]/);
  assert.match(main, /approver_group_ids: requiresApprovalTargets \? form\.approver_group_ids : \[\]/);
  assert.match(main, /otherMax > minAmount/);
  assert.match(main, /No se seleccionan Roles ni Grupos/);
});

test("direct-expense layout has explicit small-screen adaptations", async () => {
  const css = await source("src/direct-expense-form.css");

  assert.match(css, /@media \(max-width: 720px\)/);
  assert.match(css, /@media \(max-width: 440px\)/);
  assert.match(css, /grid-template-columns: minmax\(0, 1fr\)/);
  assert.match(css, /overflow-wrap: anywhere/);
  assert.match(css, /\.direct-expense-form :is\(input, select, button\) \{\s*min-height: 44px;/s);
});
