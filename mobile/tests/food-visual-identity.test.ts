import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("food cards and panel rows render the food visual to the left of the name", async () => {
  const icon = await source("src/components/nutrition/food-visual-icon.tsx");
  const card = await source("src/components/nutrition/nutrition-entity-card.tsx");
  const panel = await source("src/components/panels/entity-panels.tsx");

  assert.ok(icon.includes('[["maca", "polvo"], { emoji: "🥣", visualKey: "maca_powder" }]'));
  assert.ok(icon.includes('[["pechuga", "pollo"], { emoji: "🍗", visualKey: "chicken_breast" }]'));
  assert.ok(icon.includes('const genericVisual: FoodVisual = { emoji: "🍽️", visualKey: "food_generic" }'));
  assert.ok(card.includes('titleIcon={entity === "food" ? <FoodVisualIcon'));
  assert.ok(panel.includes('<FoodVisualIcon emoji={item.emoji} name={item.name} size="panel" visualKey={item.visualKey} />'));
  assert.ok(icon.includes('panelIcon: { fontSize: 14, lineHeight: 18, width: 20 }'));
});

test("food visual metadata travels through picker and library contracts", async () => {
  const types = await source("src/api/types.ts");
  const picker = await source("src/components/pickers/composition-picker-screen.tsx");

  assert.ok(types.includes("display_name: string; emoji: string; visual_key: string;"));
  assert.ok(types.includes("name: string; emoji?: string; visual_key?: string;"));
  assert.ok(picker.includes("foodEmoji: item.emoji"));
  assert.ok(picker.includes("foodVisualKey: item.visual_key"));
});
