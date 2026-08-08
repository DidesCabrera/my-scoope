import { NativeModule, requireOptionalNativeModule } from "expo";

import type { NutritionLabelRecognition } from "./NutritionLabelOcr.types";

declare class NutritionLabelOcrModule extends NativeModule {
  recognizeAsync(imageUri: string): Promise<NutritionLabelRecognition>;
}

const nativeModule = requireOptionalNativeModule<NutritionLabelOcrModule>("NutritionLabelOcr");

export function isNutritionLabelOcrAvailable(): boolean {
  return nativeModule !== null;
}

export async function recognizeNutritionLabel(imageUri: string): Promise<NutritionLabelRecognition> {
  if (!nativeModule) {
    throw new Error("nutrition_label_ocr_native_module_unavailable");
  }
  return nativeModule.recognizeAsync(imageUri);
}
