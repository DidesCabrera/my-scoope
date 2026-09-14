import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("food rows expose a consistent detail navigation affordance", async () => {
  const panels = await readTestFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const activeMeal = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");

  assertSourceMatch(panels, /detailId\?: number \| null/);
  assertSourceMatch(panels, /accessibilityRole="link"/);
  assertSourceMatch(panels, /onOpenItem\?\.\(item\)/);
  assertSourceMatch(detail, /`\/libraries\/foods\/\$\{food\.detailId\}`/);
  assertSourceMatch(detail, /<FoodDetailCardList items=\{foodItems\} onOpenFood=\{openFood\}/);
  assertSourceMatch(activeMeal, /<FoodDetailCardList items=\{foods\} onOpenFood=/);
});
