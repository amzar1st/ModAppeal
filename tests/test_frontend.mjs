import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(root, "dist/index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "dist/app.js"), "utf8");

assert.match(html, /ModAppeal/);
assert.match(html, /PUBLIC CASE HISTORY/);
assert.match(app, /get_case/);
assert.match(app, /LATEST_FINAL/);
assert.match(app, /TransactionStatus\.FINALIZED/);
for (const method of ["create_community", "publish_policy", "register_moderator", "record_action", "open_appeal", "submit_evidence", "submit_counter_evidence", "adjudicate", "finalize", "claim_bond"]) {
  assert.match(app, new RegExp(method));
}
assert.doesNotMatch(app, /seeded|fallback.*live|demo case/i);
console.log("ModAppeal frontend checks passed");
