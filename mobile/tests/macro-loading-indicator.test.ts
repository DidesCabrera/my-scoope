import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("the macro loading proposal uses trackless KPI allocation bars and respects reduced motion", async () => {
  const component = await fs.readFile(path.resolve(process.cwd(), "src/components/ui/macro-loading-indicator.tsx"), "utf8");
  const gallery = await fs.readFile(path.resolve(process.cwd(), "src/app/dev/ui-gallery.tsx"), "utf8");
  const componentContracts = [
    "tokens.color.protein",
    "tokens.color.carbs",
    "tokens.color.fat",
    "withRepeat(",
    "withSequence(",
    "useReducedMotion()",
    "tokens.component.nutritionKpi.regular.barHeight",
    "tokens.component.nutritionKpi.regular.barRadius",
  ];
  const galleryContracts = [
    'title="Carga entre vistas"',
    '<MacroLoadingIndicator accessibilityLabel="Preparando tu día"',
  ];

  assert.equal(componentContracts.every((contract) => component.includes(contract)), true);
  assert.equal(galleryContracts.every((contract) => gallery.includes(contract)), true);
  assert.equal(component.includes("allocationPanelTrack"), false);
  assert.equal(gallery.includes(">Preparando tu día…</Text>"), false);
});
