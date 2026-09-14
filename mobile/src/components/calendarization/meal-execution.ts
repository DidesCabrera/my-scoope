import type { MealExecutionItem } from "@/api/types";

export type NormalizedMealExecutionItem = MealExecutionItem & {
  note: string;
  prepared_food_keys: string[];
};

export function normalizeMealExecutionItem(item: MealExecutionItem): NormalizedMealExecutionItem {
  return {
    ...item,
    note: typeof item.note === "string" ? item.note : "",
    prepared_food_keys: Array.isArray(item.prepared_food_keys)
      ? item.prepared_food_keys.filter((key): key is string => typeof key === "string")
      : [],
  };
}

export function normalizeMealExecution(items: MealExecutionItem[] | null | undefined): NormalizedMealExecutionItem[] {
  return Array.isArray(items) ? items.map(normalizeMealExecutionItem) : [];
}
