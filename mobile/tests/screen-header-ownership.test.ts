import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("Screen has one implementation and never overrides externally owned headers", async () => {
  const layout = await source("src/components/ui/layout.tsx");
  const primitives = await source("src/components/ui/primitives.tsx");
  const feedback = await source("src/components/ui/feedback.tsx");

  assert.match(layout, /headerMode\?: "automatic" \| "preserve"/);
  assert.match(layout, /if \(headerMode === "preserve"\) return undefined;[\s\S]*setHeaderPresentation/);
  assert.equal((layout.match(/export function Screen/g) ?? []).length, 1);
  assert.doesNotMatch(primitives, /export function Screen/);
  assert.match(primitives, /import \{ Screen \} from "\.\/layout";[\s\S]*export \{ Screen \}/);
  assert.match(primitives, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
  assert.match(feedback, /<Screen scroll=\{false\} contentStyle=\{styles\.loadingState\} headerMode="preserve">/);
});

test("screens that own global navigation preserve their header through content and loading states", async () => {
  for (const relativePath of [
    "src/app/comparator/index.tsx",
    "src/app/assistant/index.tsx",
    "src/app/program/activate.tsx",
    "src/app/program/history.tsx",
    "src/app/program/index.tsx",
    "src/app/today.tsx",
    "src/components/pickers/composition-picker-screen.tsx",
  ]) {
    const screen = await source(relativePath);
    assert.match(screen, /useHeaderPresentation/);
    assert.match(screen, /<Screen headerMode="preserve">/);
  }

  const comparator = await source("src/app/comparator/index.tsx");
  assert.match(comparator, /mode: "back", title: savedId \? "Editar comparación" : "Nueva comparación"/);
  assert.match(comparator, /action: \{ label: "Cancelar", onPress: cancel \}/);
  assert.doesNotMatch(comparator, /title=\{savedId \? "Editar Comparación" : "Nueva Comparación"\}/);
  assert.match(comparator, /<View style=\{styles\.builderTabs\}>[\s\S]*<ComparisonKindTabs kind=\{kind\} onChange=\{changeKind\} \/>[\s\S]*<Screen headerMode="preserve">/);

  const assistant = await source("src/app/assistant/index.tsx");
  assert.match(assistant, /action: \{ icon: "plus", label: "Nuevo chat", onPress: \(\) => router\.push\("\/assistant\/new" as Href\) \}/);
  assert.doesNotMatch(assistant, /disabled: !page\.availability\.is_available/);
  assert.doesNotMatch(assistant, /<Button[^>]*label="Nuevo chat"/);
});
