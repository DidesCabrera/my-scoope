import type { MacroTotals } from "./types";

export type MealSnapshot = {
  key?: string;
  detail_id?: number | null;
  name?: string;
  hour?: string | null;
  note?: string;
  totals?: MacroTotals;
  foods?: {
    key?: string;
    component_type?: "food" | "preparation";
    detail_id?: number | null;
    source_food_id?: number | null;
    source_preparation_id?: number | null;
    source_preparation_version?: number | null;
    name?: string;
    quantity_g?: number | null;
    quantity_unit?: "g" | "ml" | null;
    portion_display_quantity?: number | null;
    portion_display_measure?: string | null;
    protein_g?: number | null;
    protein_per_kilogram?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
    total_kcal?: number | null;
    ingredients?: {
      source_food_id?: number | null;
      name?: string;
      quantity_g?: number | null;
      preparation_state?: string;
      is_condiment?: boolean;
    }[];
  }[];
};
