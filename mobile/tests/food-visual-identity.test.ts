import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(file: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), file), "utf8");
}

test("food cards use a larger visual on the right while panel rows remain compact", async () => {
  const icon = await source("src/components/nutrition/food-visual-icon.tsx");
  const card = await source("src/components/nutrition/nutrition-entity-card.tsx");
  const panel = await source("src/components/panels/entity-panels.tsx");

  assert.ok(icon.includes('[["maca", "polvo"], { emoji: "🥣", visualKey: "maca_powder" }]'));
  assert.ok(icon.includes('[["pechuga", "pollo"], { emoji: "🍗", visualKey: "chicken_breast" }]'));
  assert.ok(icon.includes('const genericVisual: FoodVisual = { emoji: "🍽️", visualKey: "food_generic" }'));
  assert.ok(card.includes('titleIcon={entity === "food" ? <FoodVisualIcon'));
  assert.ok(card.includes('titleIconPosition={entity === "food" ? "trailing" : "leading"}'));
  assert.ok(panel.includes('<FoodVisualIcon emoji={item.emoji} foodId={item.detailId} name={item.name} size="panel" visualKey={item.visualKey} />'));
  assert.ok(icon.includes('const remoteUrl = useRemoteFoodVisual(name, foodId)'));
  assert.ok(icon.includes('onError={() => setFailedUrl(remoteUrl)}'));
  assert.ok(icon.includes('panelIcon: { fontSize: 14, lineHeight: 18, width: 20 }'));
  assert.ok(icon.includes('titleIcon: { fontSize: 31, lineHeight: 39, width: 41 }'));
});

test("food visual metadata travels through picker and library contracts", async () => {
  const types = await source("src/api/types.ts");
  const picker = await source("src/components/pickers/composition-picker-screen.tsx");

  assert.ok(types.includes("display_name: string; emoji: string; visual_key: string;"));
  assert.ok(types.includes("name: string; emoji?: string; visual_key?: string;"));
  assert.ok(picker.includes("foodEmoji: item.emoji"));
  assert.ok(picker.includes("foodVisualKey: item.visual_key"));
});

test("food cards and details both place the visual after the title", async () => {
  const detail = await source("src/components/details/entity-detail-page.tsx");
  const heading = await source("src/components/ui/product.tsx");
  const card = await source("src/components/nutrition/nutrition-entity-card.tsx");

  assert.ok(detail.includes('titleIconPosition={entity === "food" ? "trailing" : "leading"}'));
  assert.ok(heading.includes('titleIconPosition = "leading"'));
  assert.ok(heading.includes('titleIconPosition === "leading" ? titleIcon : null'));
  assert.ok(heading.includes('titleIconPosition === "trailing" ? titleIcon : null'));
  assert.ok(card.includes('titleIcon={entity === "food" ? <FoodVisualIcon'));
  assert.ok(card.includes('titleIconPosition={entity === "food" ? "trailing" : "leading"}'));
  assert.ok(heading.includes('titleIconPosition={titleIconPosition}'));
});
