import type { LibraryNutrition } from "@/api/types";

export type FoodPortionMeasure = "household" | "metric";

export type FoodPortionConversion = {
  defaultPortion: number | null | undefined;
  householdAmount: number | null | undefined;
  householdMeasure: string | null | undefined;
  householdMeasureLabel: string | null | undefined;
};

export function portionGrams(value: string): number {
  const grams = Number(value.trim().replace(",", "."));
  return Number.isFinite(grams) && grams > 0 ? grams : 0;
}

export function hasHouseholdPortion(conversion: FoodPortionConversion): boolean {
  return Boolean(
    conversion.householdMeasure
    && conversion.householdMeasureLabel
    && conversion.householdAmount
    && conversion.householdAmount > 0
    && conversion.defaultPortion
    && conversion.defaultPortion > 0,
  );
}

export function defaultFoodPortionSelection(conversion: FoodPortionConversion): { measure: FoodPortionMeasure; quantity: string } {
  if (hasHouseholdPortion(conversion)) {
    return { measure: "household", quantity: String(conversion.householdAmount) };
  }
  return {
    measure: "metric",
    quantity: String(conversion.defaultPortion && conversion.defaultPortion > 0 ? conversion.defaultPortion : 100),
  };
}

export function foodPortionMetricAmount(
  quantity: string,
  measure: FoodPortionMeasure,
  conversion: FoodPortionConversion,
): number {
  const selectedAmount = portionGrams(quantity);
  if (measure !== "household") return selectedAmount;
  if (!hasHouseholdPortion(conversion)) return 0;
  return selectedAmount * Number(conversion.defaultPortion) / Number(conversion.householdAmount);
}

export function convertFoodPortionAmount(
  quantity: string,
  from: FoodPortionMeasure,
  to: FoodPortionMeasure,
  conversion: FoodPortionConversion,
): string {
  if (from === to) return quantity;
  const metricAmount = foodPortionMetricAmount(quantity, from, conversion);
  if (metricAmount <= 0 || !hasHouseholdPortion(conversion)) return quantity;
  const converted = to === "metric"
    ? metricAmount
    : metricAmount * Number(conversion.householdAmount) / Number(conversion.defaultPortion);
  return String(Number(converted.toFixed(3)));
}

export function restoredFoodPortionSelection(
  metricQuantity: number,
  displayQuantity: number | null | undefined,
  displayMeasure: string | null | undefined,
  conversion: FoodPortionConversion,
): { measure: FoodPortionMeasure; quantity: string } {
  if (hasHouseholdPortion(conversion) && displayMeasure === conversion.householdMeasure && displayQuantity && displayQuantity > 0) {
    return { measure: "household", quantity: String(displayQuantity) };
  }
  return { measure: "metric", quantity: String(metricQuantity) };
}

export function scaleFoodNutrition(nutrition: LibraryNutrition, quantity: string): LibraryNutrition {
  const grams = portionGrams(quantity);
  const factor = grams / 100;
  const hasPortion = grams > 0;

  return {
    calories: nutrition.calories * factor,
    protein: {
      ...nutrition.protein,
      allocation: hasPortion ? nutrition.protein.allocation : 0,
      grams: nutrition.protein.grams * factor,
    },
    carbs: {
      allocation: hasPortion ? nutrition.carbs.allocation : 0,
      grams: nutrition.carbs.grams * factor,
    },
    fat: {
      allocation: hasPortion ? nutrition.fat.allocation : 0,
      grams: nutrition.fat.grams * factor,
    },
  };
}
