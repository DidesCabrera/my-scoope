import type { FoodNutritionFacts } from "@/api/food-nutrition";

export type FoodNutritionFactRow = {
  id: keyof FoodNutritionFacts;
  label: string;
  value: string;
};

const NUTRIENT_DEFINITIONS: {
  id: keyof FoodNutritionFacts;
  label: string;
  unit: "g" | "mg";
}[] = [
  { id: "saturated_fat_g", label: "Grasas saturadas", unit: "g" },
  { id: "sugar_g", label: "Azúcares", unit: "g" },
  { id: "fiber_g", label: "Fibra", unit: "g" },
  { id: "sodium_mg", label: "Sodio", unit: "mg" },
];

export function formatFoodNutrient(value: number | null, unit: "g" | "mg"): string {
  if (value == null || !Number.isFinite(value)) return "Sin información";
  return `${value.toLocaleString("es-CL", { maximumFractionDigits: 1 })} ${unit}`;
}

export function foodNutritionFactRows(nutrition: FoodNutritionFacts): FoodNutritionFactRow[] {
  return NUTRIENT_DEFINITIONS.map(({ id, label, unit }) => ({
    id,
    label,
    value: formatFoodNutrient(nutrition[id], unit),
  }));
}
