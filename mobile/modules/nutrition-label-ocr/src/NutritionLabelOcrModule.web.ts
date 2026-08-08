import type { NutritionLabelRecognition } from "./NutritionLabelOcr.types";

export function isNutritionLabelOcrAvailable(): boolean {
  return false;
}

export async function recognizeNutritionLabel(_imageUri: string): Promise<NutritionLabelRecognition> {
  throw new Error("nutrition_label_ocr_native_module_unavailable");
}
