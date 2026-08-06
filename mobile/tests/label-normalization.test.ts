import assert from "node:assert/strict";
import test from "node:test";

import type { NutritionLabelRecognition } from "../modules/nutrition-label-ocr/src/NutritionLabelOcr.types";
import { normalizeNutritionLabel } from "../src/label-capture/normalize";

function recognition(lines: string[], confidence = 0.96): NutritionLabelRecognition {
  return {
    engine: "apple_vision",
    engineVersion: "1",
    durationMs: 12,
    observations: lines.map((text, index) => ({
      text,
      confidence,
      boundingBox: { x: 0.05, y: 0.05 + index * 0.06, width: 0.9, height: 0.03 },
    })),
  };
}

test("normalizes a Spanish per-100g nutrition label with decimal commas", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Información nutricional por 100 g",
    "Energía (kcal) 245",
    "Proteínas 10,5 g",
    "Carbohidratos 32,0 g",
    "Grasas totales 8,2 g",
    "Grasa saturada 2,1 g",
    "Sodio 125 mg",
  ]));

  assert.equal(draft.basis, "per_100g");
  assert.equal(draft.values.protein_g, 10.5);
  assert.equal(draft.values.carbs_g, 32);
  assert.equal(draft.values.fat_g, 8.2);
  assert.equal(draft.values.saturated_fat_g, 2.1);
  assert.equal(draft.values.sodium_mg, 125);
});

test("converts values declared for one serving into the 100g food contract", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Porción 40 g",
    "Energía 100 kcal",
    "Proteínas 4 g",
    "Carbohidratos 12 g",
    "Grasa total 4 g",
  ]));

  assert.equal(draft.basis, "per_serving");
  assert.equal(draft.servingSizeG, 40);
  assert.equal(draft.values.energy_kcal, 250);
  assert.equal(draft.values.protein_g, 10);
  assert.equal(draft.values.carbs_g, 30);
  assert.equal(draft.values.fat_g, 10);
  assert.ok(draft.warnings.includes("basis_normalized_from_serving"));
});

test("uses the 100g column when a dual-column label lists serving first", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Porción 50 g     100 g",
    "Proteínas (g) 5 10",
    "Carbohidratos (g) 15 30",
    "Grasas totales (g) 2 4",
  ]));

  assert.equal(draft.basis, "per_100g");
  assert.equal(draft.values.protein_g, 10);
  assert.equal(draft.values.carbs_g, 30);
  assert.equal(draft.values.fat_g, 4);
});

test("exposes missing and low-confidence fields instead of inventing values", () => {
  const draft = normalizeNutritionLabel(recognition(["Información nutricional", "Proteínas 8 g"], 0.6));

  assert.equal(draft.basis, "manual");
  assert.equal(draft.values.protein_g, 8);
  assert.equal(draft.values.carbs_g, undefined);
  assert.ok(draft.warnings.includes("protein_g_low_confidence"));
  assert.ok(draft.warnings.includes("carbs_g_missing"));
  assert.ok(draft.warnings.includes("fat_g_missing"));
});
