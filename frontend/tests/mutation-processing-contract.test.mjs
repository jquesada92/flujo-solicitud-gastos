import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const governor = read("../src/request-governor.js");
const actionState = read("../src/action-state.css");
const iam = read("../src/iam-admin.jsx");
const main = read("../src/main.jsx");

test("API mutations use one blocking processing overlay with concurrency", () => {
  assert.match(governor, /new Set\(\["POST", "PUT", "PATCH", "DELETE"\]\)/);
  assert.match(governor, /if \(blockForMutation\) beginBlockingMutation\(\)/);
  assert.match(governor, /activeBlockingMutations \+= 1/);
  assert.match(governor, /activeBlockingMutations = Math\.max\(0, activeBlockingMutations - 1\)/);
  assert.match(governor, /finally \{\s*if \(blockForMutation\) endBlockingMutation\(\)/);
  assert.match(governor, /element\.setAttribute\("inert", ""\)/);
  assert.match(governor, /role", "alertdialog"/);
  assert.match(governor, /Procesando…/);
});

test("background activity does not interrupt the user", () => {
  assert.match(governor, /BACKGROUND_MUTATION_PATHS = new Set\(\["\/api\/auth\/activity"\]\)/);
  assert.match(main, /api\("\/api\/auth\/activity", \{ method: "POST", appMutationOverlay: false \}\)/);
});

test("processing overlay covers narrow and wide viewports", () => {
  assert.match(actionState, /\.app-processing-overlay \{/);
  assert.match(actionState, /position: fixed/);
  assert.match(actionState, /inset: 0/);
  assert.match(actionState, /z-index: 2147483646/);
  assert.match(actionState, /safe-area-inset-bottom/);
  assert.match(actionState, /@media \(max-width: 440px\)/);
});

test("successful role creation resets identity and values before the next POST", () => {
  assert.match(iam, /const creating = !target/);
  assert.match(iam, /if \(creating\) \{\s*setSelectedId\(null\);\s*setRecovery\(null\);\s*setForm\(emptyRoleForm\(\)\)/);
  assert.match(iam, /\} else \{\s*setRecovery\(null\);\s*setSelectedId\(saved\.id\)/);
  assert.match(iam, /if \(!canPersistRole \|\| savingRole\) return/);
  assert.match(iam, /disabled=\{!canPersistRole \|\| savingRole\}/);
});
