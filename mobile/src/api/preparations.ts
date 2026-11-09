export type LibraryPreparationPanelItem = {
  relation_id: number;
  detail_id: number;
  name: string;
  version: number;
  quantity_g: number;
  selected_units: number | null;
  selection_mode: "units" | "grams";
  household_label: string;
  calories: number;
  sodium_mg: number | null;
  allergens: string[];
  ingredients: { food_id: number; name: string; quantity_g: number; preparation_state: string; is_condiment: boolean }[];
};
