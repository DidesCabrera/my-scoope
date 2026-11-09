import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("food rows expose a consistent detail navigation affordance", async () => {
  const panels = await readTestFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const activeMeal = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id]/meals/[mealKey].tsx"), "utf8");

  assertSourceMatch(panels, /detailId\?: number \| null/);
  assertSourceMatch(panels, /accessibilityRole="link"/);
  assertSourceMatch(panels, /onOpenItem\?\.\(item\)/);
  assertSourceDoesNotMatch(panels, /<ChevronRight color=\{tokens\.color\.textMuted\} size=\{17\}/);
  assertSourceMatch(detail, /`\/libraries\/foods\/\$\{food\.detailId\}`/);
  assertSourceMatch(detail, /<FoodDetailCardList editing=\{\(component\) => component\.kind === "preparation" \? preparationEditing : foodEditing\} items=\{foodItems\} onOpenFood=\{openFood\}/);
  assertSourceMatch(activeMeal, /<FoodDetailCardList editing=\{\(\) => foodEditing\} items=\{foods\} onOpenFood=/);
});

test("meal component cards offer portion, replacement, and scoped removal before detail navigation", async () => {
  const cards = await readTestFile(path.resolve(process.cwd(), "src/components/details/food-detail-card-list.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const picker = await readTestFile(path.resolve(process.cwd(), "src/app/pickers/preparation-to-meal.tsx"), "utf8");

  assertSourceMatch(cards, /label: "Editar porción"/);
  assertSourceMatch(cards, /label: `Reemplazar \$\{componentLabel\}`/);
  assertSourceMatch(cards, /label: `Quitar \$\{componentLabel\}`/);
  assertSourceMatch(cards, /<ContextCardActions[\s\S]*?<EntityCardAction label=\{`Ver detalle/);
  assertSourceMatch(detail, /\/preparations\/\$\{preparation\.relationId\}`, \{ method: "DELETE" \}/);
  assertSourceMatch(detail, /relationId: String\(preparation\.relationId\), replace: "1"/);
  assertSourceMatch(picker, /relation && replace !== "1" \? payload : \{ preparation_id: selected\.id, \.\.\.payload \}/);
});

test("meal component cards expose contextual food and preparation panels, collapsed initially", async () => {
  const cards = await readTestFile(path.resolve(process.cwd(), "src/components/details/food-detail-card-list.tsx"), "utf8");
  const nutritionCard = await readTestFile(path.resolve(process.cwd(), "src/components/nutrition/nutrition-entity-card.tsx"), "utf8");

  assertSourceMatch(cards, /collapsiblePanel=\{item\.detailId != null\}/);
  assertSourceMatch(cards, /<PreparationComponentPanel item=\{item\} key=[^\n]+ onOpenFood=\{onOpenFood\}/);
  assertSourceMatch(cards, /<FoodPanels items=\{detail\.ingredients\.map/);
  assertSourceMatch(cards, /<PickerFoodNutritionPanel foodId=\{item\.detailId\} key=\{item\.detailId\} portion=/);
  assertSourceMatch(nutritionCard, /initialPanelExpanded = false/);
});

test("menu rows always use their meal detail when no contextual route is provided", async () => {
  const panels = await readTestFile(path.resolve(process.cwd(), "src/components/panels/entity-panels.tsx"), "utf8");
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-detail-screen.tsx"), "utf8");
  const calendarizedDay = await readTestFile(path.resolve(process.cwd(), "src/app/program/days/[id].tsx"), "utf8");
  const libraryCard = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"), "utf8");
  const libraryPanels = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/entity-panels.tsx"), "utf8");

  assertSourceMatch(panels, /const openItem = onOpenItem \?\? \(orderedItems\.some\(\(item\) => item\.detailId != null\) \? \(item: MealPanelItem\) =>/);
  assertSourceMatch(panels, /router\.push\(`\/libraries\/meals\/\$\{item\.detailId\}` as Href\)/);
  assertSourceMatch(panels, /<MealMenuPanel editing=\{rowEditing\} items=\{orderedItems\} onOpenItem=\{openItem\}/);
  assertSourceMatch(detail, /<MealPanels editing=\{mealEditing\} items=\{mealItems\} nestedScroll onOpenItem=\{mealEditing\?\.onOpen\}/);
  assertSourceMatch(calendarizedDay, /const openMeal = \(meal: MealPanelItem\) => router\.push\(\{[\s\S]*?pathname: "\/program\/days\/\[id\]\/meals\/\[mealKey\]"/);
  assertSourceMatch(calendarizedDay, /<MealPanels[\s\S]*?items=\{mealItems\}[\s\S]*?onOpenItem=\{openMeal\}/);
  assertSourceMatch(libraryCard, /<MealPanels dailyPlanId=\{item\.entity === "dailyPlan" \? item\.id : undefined\} editing=\{mealEditing\} items=\{item\.panel\.meals\}/);
  assertSourceMatch(libraryPanels, /dailyPlanMealId: String\(meal\.relationId\)/);
  assertSourceMatch(libraryPanels, /mealTime: meal\.time \?\? ""/);
});
