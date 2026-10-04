import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("library detail menus expose comparison for supported entities", async () => {
  const actions = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-actions.tsx"), "utf8");
  const detail = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");

  assert.match(actions, /onCompare\?: \(\) => void[\s\S]*<Scale color=\{tokens\.color\.textMain\}[\s\S]*>Comparar</);
  assert.match(detail, /useComparatorSelectionTransfer[\s\S]*item\.entity === "food" \? "foods" : item\.entity === "meal" \? "meals" : "dailyplans"/);
  assert.match(detail, /publishSelection\(\{[\s\S]*option: \{[\s\S]*id: item\.id,[\s\S]*name: item\.name,[\s\S]*slotKey: 1/);
  assert.match(detail, /pathname: "\/comparator", params: \{ create: "1", kind \}[\s\S]*onCompare=\{item\.entity === "program" \? undefined : openComparison\}/);
});
