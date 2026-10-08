import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const root = path.resolve(__dirname, "..");
const screen = fs.readFileSync(path.join(root, "src/app/assistant/index.tsx"), "utf8");
const actions = fs.readFileSync(path.join(root, "src/components/assistant/assistant-list-actions.tsx"), "utf8");
const editor = fs.readFileSync(path.join(root, "src/components/assistant/assistant-list-editor.tsx"), "utf8");

test("offers list editing from both assistant section menus", () => {
  assert.ok(actions.includes('label="Editar lista"'));
  assert.ok(screen.includes('"Acciones de Propuestas"'));
});

test("keeps the new-chat action beside the menu in both tabs", () => {
  assert.ok(screen.includes('createAction: { icon: "plus", label: "Nuevo chat"'));
  assert.ok(!actions.includes('label="Nuevo chat"'));
});

test("supports individual and bulk deletion without manual ordering", () => {
  assert.ok(screen.includes("/api/v1/ai/chats/bulk-delete"));
  assert.ok(screen.includes("/api/v1/proposals/bulk-delete"));
  assert.ok(editor.includes('accessibilityRole="checkbox"'));
  assert.ok(editor.includes("onDelete(item)"));
  assert.ok(!editor.includes("DraggableFlatList"));
  assert.ok(!screen.includes("/order"));
});
