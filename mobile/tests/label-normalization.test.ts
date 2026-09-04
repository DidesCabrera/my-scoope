import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import type { NutritionLabelRecognition } from "../modules/nutrition-label-ocr/src/NutritionLabelOcr.types";
import {
  confirmNutritionLabelBasis,
  convertServingDraftTo100g,
  normalizeNutritionLabel,
} from "../src/label-capture/normalize";

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

test("detects grams when a serving is expressed as units with a parenthesized weight", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Porción: 1 unidad (30 g)",
    "Energía 120 kcal",
    "Proteínas 4 g",
    "Carbohidratos 18 g",
    "Grasa total 4 g",
  ]));

  assert.equal(draft.basis, "per_serving");
  assert.equal(draft.servingSizeG, 30);
  assert.equal(draft.normalizationStatus, "ready");
  assert.equal(draft.values.protein_g, 13.333);
  assert.equal(draft.values.carbs_g, 60);
  assert.equal(draft.values.fat_g, 13.333);
});

test("does not expose per-serving readings as per-100g values when serving weight is missing", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Cantidad por porción",
    "Energía 120 kcal",
    "Proteínas 4 g",
    "Carbohidratos 18 g",
    "Grasa total 4 g",
  ]));

  assert.equal(draft.basis, "per_serving");
  assert.equal(draft.normalizationStatus, "serving_size_required");
  assert.equal(draft.sourceValues.protein_g, 4);
  assert.deepEqual(draft.values, {});
  assert.ok(draft.warnings.includes("serving_size_required"));
});

test("converts fail-closed per-serving readings after the user supplies the missing weight", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Cantidad por porción",
    "Energía 120 kcal",
    "Proteínas 4 g",
    "Carbohidratos 18 g",
    "Grasa total 4 g",
  ]));
  const converted = convertServingDraftTo100g(draft, 30);

  assert.equal(converted.normalizationStatus, "ready");
  assert.equal(converted.servingSizeG, 30);
  assert.equal(converted.values.protein_g, 13.333);
  assert.equal(converted.values.carbs_g, 60);
  assert.equal(converted.values.fat_g, 13.333);
  assert.ok(converted.warnings.includes("basis_normalized_from_serving"));
  assert.ok(!converted.warnings.includes("serving_size_required"));
});

test("uses the 100g column when a dual-column label lists serving first", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Porción 50 g     100 g",
    "Proteínas (g) 5 10",
    "Carbohidratos (g) 15 30",
    "Grasas totales (g) 2 4",
  ]));

  assert.equal(draft.basis, "per_100g");
  assert.equal(draft.servingSizeG, 50);
  assert.equal(draft.values.protein_g, 10);
  assert.equal(draft.values.carbs_g, 30);
  assert.equal(draft.values.fat_g, 4);
});

test("uses the 100g column when a dual-column label lists 100g first", () => {
  const draft = normalizeNutritionLabel(recognition([
    "100 g     Porción 50 g",
    "Proteínas (g) 10 5",
    "Carbohidratos (g) 30 15",
    "Grasas totales (g) 4 2",
  ]));

  assert.equal(draft.basis, "per_100g");
  assert.equal(draft.servingSizeG, 50);
  assert.equal(draft.values.protein_g, 10);
  assert.equal(draft.values.carbs_g, 30);
  assert.equal(draft.values.fat_g, 4);
});

test("exposes missing and low-confidence fields instead of inventing values", () => {
  const draft = normalizeNutritionLabel(recognition(["Información nutricional", "Proteínas 8 g"], 0.6));

  assert.equal(draft.basis, "manual");
  assert.equal(draft.normalizationStatus, "basis_confirmation_required");
  assert.equal(draft.sourceValues.protein_g, 8);
  assert.equal(draft.values.protein_g, undefined);
  assert.equal(draft.values.carbs_g, undefined);
  assert.ok(draft.warnings.includes("protein_g_low_confidence"));
  assert.ok(draft.warnings.includes("carbs_g_missing"));
  assert.ok(draft.warnings.includes("fat_g_missing"));
});

test("requires explicit basis confirmation when OCR misses the table header", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Proteínas 10 g",
    "Carbohidratos 20 g",
    "Grasas totales 5 g",
  ]));

  assert.equal(draft.normalizationStatus, "basis_confirmation_required");
  assert.deepEqual(draft.values, {});

  const confirmed = confirmNutritionLabelBasis(draft, "per_100g");
  assert.equal(confirmed.basis, "per_100g");
  assert.equal(confirmed.normalizationStatus, "ready");
  assert.equal(confirmed.values.protein_g, 10);
  assert.ok(confirmed.warnings.includes("basis_confirmed_as_per_100g"));
});

test("routes an explicitly confirmed per-serving basis through the conversion gate", () => {
  const draft = normalizeNutritionLabel(recognition([
    "Proteínas 4 g",
    "Carbohidratos 18 g",
    "Grasas totales 4 g",
  ]));
  const perServing = confirmNutritionLabelBasis(draft, "per_serving");

  assert.equal(perServing.basis, "per_serving");
  assert.equal(perServing.normalizationStatus, "serving_size_required");
  assert.deepEqual(perServing.values, {});
});

test("the capture screen supports camera and gallery with explicit AI safeguards", async () => {
  const screen = await readFile(path.resolve(process.cwd(), "src/app/label-capture.tsx"), "utf8");

  for (const expected of [
    'autofocus="on"',
    "enableTorch={torchEnabled}",
    "launchImageLibraryAsync",
    "prepareLabelImage",
    "consent_to_ai_processing: true",
    'retain_label_image: Boolean(retainImage && prepared && analysisId)',
    '"/api/v1/foods/label-captures/analyze"',
    'loading={openingCamera}',
  ]) {
    assert.ok(screen.includes(expected), `missing capture safeguard: ${expected}`);
  }
  assert.ok(!screen.includes("development build iOS de CML05"));
  assert.ok(!screen.includes("CameraView.isAvailableAsync()"));
});

test("the native OCR module uses nutrition vocabulary and versioned provenance", async () => {
  const module = await readFile(
    path.resolve(process.cwd(), "modules/nutrition-label-ocr/ios/NutritionLabelOcrModule.swift"),
    "utf8",
  );

  for (const expected of [
    '"engineVersion": "2"',
    "request.customWords = [",
    '"Proteínas"',
    '"Carbohidratos"',
  ]) {
    assert.ok(module.includes(expected), `missing native OCR safeguard: ${expected}`);
  }
});
