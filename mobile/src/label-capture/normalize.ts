import type {
  NutritionLabelObservation,
  NutritionLabelRecognition,
} from "../../modules/nutrition-label-ocr/src/NutritionLabelOcr.types";

export type NutritionField =
  | "energy_kcal"
  | "protein_g"
  | "carbs_g"
  | "fat_g"
  | "saturated_fat_g"
  | "sugar_g"
  | "fiber_g"
  | "sodium_mg";

export type NutritionLabelDraft = {
  basis: "per_100g" | "per_serving" | "manual";
  servingSizeG: number | null;
  sourceValues: Partial<Record<NutritionField, number>>;
  values: Partial<Record<NutritionField, number>>;
  fieldConfidence: Partial<Record<NutritionField | "serving_size_g", number>>;
  warnings: string[];
  normalizationStatus: "ready" | "basis_confirmation_required" | "serving_size_required";
  ocrEngine: string;
  ocrEngineVersion: string;
};

type Row = { text: string; confidence: number };

const definitions: { key: NutritionField; pattern: RegExp }[] = [
  { key: "saturated_fat_g", pattern: /grasas?\s+saturadas?|saturated\s+fat/i },
  { key: "sugar_g", pattern: /az[uú]cares?(?:\s+totales?)?|(?:total\s+)?sugars?/i },
  { key: "fiber_g", pattern: /fibra\s+(?:dietaria|alimentaria)|dietary\s+fiber|\bfibra\b/i },
  { key: "sodium_mg", pattern: /\bsodio\b|\bsodium\b/i },
  { key: "protein_g", pattern: /prote[ií]nas?|\bprotein\b/i },
  { key: "carbs_g", pattern: /carbohidratos?|hidratos?\s+de\s+carbono|(?:total\s+)?carbohydrate/i },
  { key: "fat_g", pattern: /grasas?\s+totales?|total\s+fat|l[ií]pidos?|^\s*grasas?(?!\s+saturad)\b|^\s*fat\b/i },
  { key: "energy_kcal", pattern: /energ[ií]a|valor\s+energ[eé]tico|calor[ií]as?|\benergy\b/i },
];

function plain(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function rounded(value: number, digits = 3): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function rowsFromObservations(observations: NutritionLabelObservation[]): Row[] {
  const positioned = observations
    .filter((item) => item.text.trim())
    .sort((left, right) => {
      const yDistance = left.boundingBox.y - right.boundingBox.y;
      return Math.abs(yDistance) > 0.015 ? yDistance : left.boundingBox.x - right.boundingBox.x;
    });
  const rows: { centerY: number; items: NutritionLabelObservation[] }[] = [];
  for (const observation of positioned) {
    const centerY = observation.boundingBox.y + observation.boundingBox.height / 2;
    const current = rows.at(-1);
    if (current && Math.abs(current.centerY - centerY) <= Math.max(0.018, observation.boundingBox.height * 0.6)) {
      current.items.push(observation);
      current.centerY = (current.centerY + centerY) / 2;
    } else {
      rows.push({ centerY, items: [observation] });
    }
  }
  return rows.map((row) => {
    const items = row.items.sort((left, right) => left.boundingBox.x - right.boundingBox.x);
    return {
      text: items.map((item) => item.text.trim()).join(" "),
      confidence: Math.min(...items.map((item) => item.confidence)),
    };
  });
}

function numericTokens(value: string): number[] {
  const result: number[] = [];
  const pattern = /\d+(?:[.,]\d+)?/g;
  for (const match of value.matchAll(pattern)) {
    const rest = value.slice((match.index ?? 0) + match[0].length);
    if (/^\s*%/.test(rest)) continue;
    result.push(Number(match[0].replace(",", ".")));
  }
  return result.filter(Number.isFinite);
}

function selectedColumn(values: number[], per100AfterServing: boolean | null): number | null {
  if (!values.length) return null;
  if (values.length === 1 || per100AfterServing === null) return values[0];
  return per100AfterServing ? values.at(-1) ?? null : values[0];
}

function energyValue(value: string, per100AfterServing: boolean | null): number | null {
  const kcal: number[] = [];
  const kilojoules: number[] = [];
  for (const match of value.matchAll(/(\d+(?:[.,]\d+)?)\s*(kcal|kj)\b/gi)) {
    const number = Number(match[1].replace(",", "."));
    if (match[2].toLowerCase() === "kcal") kcal.push(number);
    else kilojoules.push(number);
  }
  const kcalValue = selectedColumn(kcal, per100AfterServing);
  if (kcalValue !== null) return kcalValue;
  const kjValue = selectedColumn(kilojoules, per100AfterServing);
  if (kjValue !== null) return kjValue / 4.184;
  const untagged = numericTokens(value);
  if (/\bkj\b.*\bkcal\b/i.test(value) && untagged.length >= 2) return untagged.at(-1) ?? null;
  const fallback = selectedColumn(untagged, per100AfterServing);
  if (fallback === null) return null;
  return /\bkj\b/i.test(value) && !/\bkcal\b/i.test(value) ? fallback / 4.184 : fallback;
}

function valueForRow(row: Row, key: NutritionField, pattern: RegExp, per100AfterServing: boolean | null): number | null {
  const label = pattern.exec(row.text);
  if (!label) return null;
  const afterLabel = row.text.slice((label.index ?? 0) + label[0].length);
  if (key === "energy_kcal") return energyValue(afterLabel, per100AfterServing);
  const value = selectedColumn(numericTokens(afterLabel), per100AfterServing);
  if (value === null) return null;
  if (key === "sodium_mg" && /\bg\b/i.test(row.text) && !/\bmg\b/i.test(row.text)) return value * 1000;
  return value;
}

function detectServingSize(rows: Row[]): number | null {
  for (const row of rows) {
    const portion = /(?:porci[oó]n\b|serving\s+size\b)/i.exec(row.text);
    if (!portion) continue;
    const afterPortion = row.text.slice((portion.index ?? 0) + portion[0].length);
    const match = /(\d+(?:[.,]\d+)?)\s*g\b/i.exec(afterPortion);
    if (match) return Number(match[1].replace(",", "."));
  }
  return null;
}

function maximumFor(key: NutritionField): number {
  if (key === "sodium_mg") return 100_000;
  if (key === "energy_kcal") return 10_000;
  return 100;
}

function normalizedValues(
  sourceValues: NutritionLabelDraft["sourceValues"],
  factor: number,
  warnings: string[],
): NutritionLabelDraft["values"] {
  const values: NutritionLabelDraft["values"] = {};
  for (const [key, raw] of Object.entries(sourceValues) as [NutritionField, number][]) {
    const normalized = raw * factor;
    if (normalized < 0 || normalized > maximumFor(key)) {
      warnings.push(`${key}_outside_expected_range`);
      continue;
    }
    values[key] = rounded(normalized);
  }
  return values;
}

function appendEnergyWarning(values: NutritionLabelDraft["values"], warnings: string[]) {
  if (values.energy_kcal === undefined || values.protein_g === undefined || values.carbs_g === undefined || values.fat_g === undefined) return;
  const macroEnergy = values.protein_g * 4 + values.carbs_g * 4 + values.fat_g * 9;
  if (Math.abs(values.energy_kcal - macroEnergy) > Math.max(20, values.energy_kcal * 0.2)) {
    warnings.push("energy_macro_mismatch");
  }
}

export function normalizeNutritionLabel(recognition: NutritionLabelRecognition): NutritionLabelDraft {
  const rows = rowsFromObservations(recognition.observations);
  const allText = rows.map((row) => row.text).join("\n");
  const normalizedText = plain(allText);
  const hundredIndex = normalizedText.search(/\b100\s*g\b/);
  const servingIndex = normalizedText.search(/\bporcion\b|\bserving\b/);
  const hasPer100 = hundredIndex >= 0;
  const hasServing = servingIndex >= 0;
  const basis: NutritionLabelDraft["basis"] = hasPer100 ? "per_100g" : hasServing ? "per_serving" : "manual";
  const servingSizeG = detectServingSize(rows);
  const per100AfterServing = hasPer100 && hasServing ? hundredIndex > servingIndex : null;
  const sourceValues: NutritionLabelDraft["sourceValues"] = {};
  const fieldConfidence: NutritionLabelDraft["fieldConfidence"] = {};
  const warnings: string[] = [];

  for (const definition of definitions) {
    const row = rows.find((candidate) => definition.pattern.test(candidate.text));
    if (!row) continue;
    const raw = valueForRow(row, definition.key, definition.pattern, per100AfterServing);
    if (raw === null) continue;
    if (raw < 0 || raw > maximumFor(definition.key)) {
      warnings.push(`${definition.key}_outside_expected_range`);
      continue;
    }
    sourceValues[definition.key] = rounded(raw);
    fieldConfidence[definition.key] = rounded(row.confidence, 2);
    if (row.confidence < 0.75) warnings.push(`${definition.key}_low_confidence`);
  }
  if (servingSizeG) fieldConfidence.serving_size_g = 0.9;
  if (basis === "manual") warnings.push("basis_not_detected");
  if (basis === "per_serving" && !servingSizeG) warnings.push("serving_size_required");
  if (basis === "per_serving" && servingSizeG) warnings.push("basis_normalized_from_serving");
  for (const key of ["protein_g", "carbs_g", "fat_g"] as const) {
    if (sourceValues[key] === undefined) warnings.push(`${key}_missing`);
  }
  const normalizationStatus = basis === "manual"
    ? "basis_confirmation_required"
    : basis === "per_serving" && !servingSizeG
      ? "serving_size_required"
      : "ready";
  const factor = basis === "per_serving" && servingSizeG ? 100 / servingSizeG : 1;
  const values = normalizationStatus === "ready" ? normalizedValues(sourceValues, factor, warnings) : {};
  appendEnergyWarning(normalizationStatus === "ready" ? values : sourceValues, warnings);

  return {
    basis,
    servingSizeG,
    sourceValues,
    values,
    fieldConfidence,
    warnings: [...new Set(warnings)],
    normalizationStatus,
    ocrEngine: recognition.engine,
    ocrEngineVersion: recognition.engineVersion,
  };
}

export function confirmNutritionLabelBasis(
  draft: NutritionLabelDraft,
  basis: "per_100g" | "per_serving",
): NutritionLabelDraft {
  if (draft.normalizationStatus !== "basis_confirmation_required") {
    throw new Error("basis_already_confirmed");
  }
  const warnings = draft.warnings.filter((warning) => (
    warning !== "basis_not_detected"
    && warning !== "serving_size_required"
    && warning !== "basis_normalized_from_serving"
    && warning !== "energy_macro_mismatch"
    && !warning.endsWith("_outside_expected_range")
  ));
  if (basis === "per_serving") {
    warnings.push("serving_size_required");
    return {
      ...draft,
      basis,
      servingSizeG: null,
      values: {},
      warnings: [...new Set(warnings)],
      normalizationStatus: "serving_size_required",
    };
  }
  warnings.push("basis_confirmed_as_per_100g");
  const values = normalizedValues(draft.sourceValues, 1, warnings);
  appendEnergyWarning(values, warnings);
  return {
    ...draft,
    basis,
    servingSizeG: null,
    values,
    warnings: [...new Set(warnings)],
    normalizationStatus: "ready",
  };
}

export function convertServingDraftTo100g(
  draft: NutritionLabelDraft,
  servingSizeG: number,
): NutritionLabelDraft {
  if (draft.basis !== "per_serving" || !Number.isFinite(servingSizeG) || servingSizeG <= 0 || servingSizeG > 10_000) {
    throw new Error("invalid_serving_size");
  }
  const warnings = draft.warnings.filter((warning) => (
    warning !== "serving_size_required"
    && warning !== "basis_normalized_from_serving"
    && warning !== "energy_macro_mismatch"
    && !warning.endsWith("_outside_expected_range")
  ));
  warnings.push("basis_normalized_from_serving");
  const values = normalizedValues(draft.sourceValues, 100 / servingSizeG, warnings);
  appendEnergyWarning(values, warnings);
  return {
    ...draft,
    servingSizeG,
    values,
    warnings: [...new Set(warnings)],
    normalizationStatus: "ready",
  };
}
