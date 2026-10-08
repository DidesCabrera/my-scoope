import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("subscription attribute tables belong to the shared UI system", async () => {
  const [gallery, planCard, table, uiIndex] = await Promise.all([
    source("src/app/dev/ui-gallery.tsx"),
    source("src/components/subscriptions/subscription-plan-card.tsx"),
    source("src/components/ui/key-value-table.tsx"),
    source("src/components/ui/index.ts"),
  ]);

  assert.match(uiIndex, /export \* from "\.\/key-value-table"/);
  assert.match(planCard, /<KeyValueTable items=\{benefits\.map/);
  assert.match(gallery, /title="Tabla de atributos"/);
  assert.match(gallery, /title="Con iconos"/);
  assert.match(gallery, /title="Sin iconos"/);
  assert.equal(gallery.match(/<KeyValueTable items=/g)?.length, 2);
  assert.match(table, /borderBottomColor: tokens\.color\.borderSoft/);
  assert.match(table, /textAlign: "right"/);
  assert.match(table, /last && styles\.rowLast/);
  assert.match(table, /return item\.onPress \?/);
  assert.match(table, /accessibilityRole="button"/);
  assert.match(table, /key=\{item\.id \?\? item\.label\}/);
  assert.match(table, /onPress=\{item\.onPress\}/);
  assert.match(table, /accessory\?: ReactNode/);
  assert.match(table, /\{item\.accessory\}/);
  assert.doesNotMatch(table, /ReanimatedSwipeable|swipeAction|SwipeableMethods/);
});
