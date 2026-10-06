import type { NutritionLabelImageQualityMetrics } from "../../modules/nutrition-label-ocr/src/NutritionLabelOcr.types";

export type LabelImageQualityIssue =
  | "too_dark"
  | "overexposed"
  | "blurry"
  | "text_too_small"
  | "no_text_detected"
  | "low_text_confidence";

export type LabelImageQuality = {
  status: "suitable" | "reviewable" | "unsuitable" | "unavailable";
  issues: LabelImageQualityIssue[];
  metrics: NutritionLabelImageQualityMetrics | null;
};

export const unavailableLabelImageQuality: LabelImageQuality = {
  status: "unavailable",
  issues: [],
  metrics: null,
};

export function classifyLabelImageQuality(
  metrics: NutritionLabelImageQualityMetrics,
): LabelImageQuality {
  const blocking: LabelImageQualityIssue[] = [];
  const warnings: LabelImageQualityIssue[] = [];

  if (metrics.brightness < 0.08) blocking.push("too_dark");
  else if (metrics.brightness < 0.18) warnings.push("too_dark");
  if (metrics.brightness > 0.97) blocking.push("overexposed");
  else if (metrics.brightness > 0.91) warnings.push("overexposed");
  if (metrics.sharpness < 0.018) blocking.push("blurry");
  else if (metrics.sharpness < 0.035) warnings.push("blurry");
  if (metrics.textObservationCount === 0) blocking.push("no_text_detected");
  else if (metrics.textObservationCount < 4 || metrics.textCoverage < 0.012) {
    warnings.push("text_too_small");
  }
  if (metrics.textObservationCount > 0 && metrics.averageTextConfidence < 0.62) {
    warnings.push("low_text_confidence");
  }

  const issues = [...new Set([...blocking, ...warnings])];
  return {
    status: blocking.length ? "unsuitable" : warnings.length ? "reviewable" : "suitable",
    issues,
    metrics,
  };
}

export function labelImageQualityMessage(issue: LabelImageQualityIssue): string {
  const messages: Record<LabelImageQualityIssue, string> = {
    too_dark: "Hay muy poca luz. Busca un lugar más iluminado o enciende la luz de la cámara.",
    overexposed: "La etiqueta tiene reflejos o zonas demasiado iluminadas. Inclina ligeramente el envase o apaga la luz.",
    blurry: "El texto está desenfocado. Aléjate un poco, mantén el teléfono firme y usa zoom.",
    text_too_small: "El texto ocupa muy poco espacio. Acerca con zoom sin aproximar demasiado el teléfono.",
    no_text_detected: "No detectamos texto legible. Encuadra únicamente la tabla nutricional.",
    low_text_confidence: "La lectura local tiene baja confianza. Revisa la nitidez y el encuadre antes de continuar.",
  };
  return messages[issue];
}
