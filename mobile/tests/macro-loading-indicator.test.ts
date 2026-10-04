import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the macro loading proposal uses trackless KPI allocation bars and respects reduced motion", async () => {
  const component = await fs.readFile(path.resolve(process.cwd(), "src/components/ui/macro-loading-indicator.tsx"), "utf8");
  const gallery = await fs.readFile(path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"), "utf8");
  const productSources = await Promise.all([
    "src/components/ui/feedback.tsx",
    "src/components/ui/primitives.tsx",
    "src/components/libraries/library-detail-screen.tsx",
    "src/components/libraries/library-list-screen.tsx",
    "src/app/program/days/[id].tsx",
    "src/app/program/days/[id]/meals/[mealKey].tsx",
    "src/app/oauth/callback.tsx",
  ].map((source) => fs.readFile(path.resolve(process.cwd(), source), "utf8")));
  const componentContracts = [
    "tokens.color.protein",
    "tokens.color.carbs",
    "tokens.color.fat",
    "protein: [45, 70, 35, 45]",
    "carbs: [60, 30, 75, 60]",
    "fat: [30, 50, 20, 30]",
    "SPEED_PERCENT_PER_SECOND = 88",
    "START_DELAY = { protein: 0, carbs: 140, fat: 280 }",
    "withRepeat(",
    "withSequence(",
    "Easing.linear",
    "transitionDuration(values[index], value)",
    'width: `${width.value}%`',
    "useReducedMotion()",
    "tokens.component.nutritionKpi.regular.barHeight",
    "tokens.component.nutritionKpi.regular.barRadius",
    "translateX: 18",
    "barHeight * 0.72",
    "contentGap * 0.72",
    "width: 79.2",
  ];
  const galleryContracts = [
    'title="Carga entre vistas"',
    '<MacroLoadingIndicator accessibilityLabel="Preparando tu día"',
  ];

  assert.equal(componentContracts.every((contract) => component.includes(contract)), true);
  assert.equal(galleryContracts.every((contract) => gallery.includes(contract)), true);
  assert.equal(productSources.every((source) => source.includes("MacroLoadingIndicator") || source.includes("<LoadingState")), true);
  assert.equal(productSources.every((source) => source.includes("surfaceApp") || source.includes("<LoadingState")), true);
  assert.equal(productSources[3].includes('if (loading && mode === "list" && !page) return <LoadingState'), true);
  assert.equal(component.includes("allocationPanelTrack"), false);
  assert.equal(component.includes("Easing.inOut"), false);
  assert.equal(component.includes("withDelay("), true);
  assert.equal(component.includes("const cycle"), false);
  assert.equal(gallery.includes(">Preparando tu día…</Text>"), false);
});
