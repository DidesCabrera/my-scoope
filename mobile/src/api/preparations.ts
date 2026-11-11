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
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  sodium_mg: number | null;
  allergens: string[];
  ingredients: PreparationComponentDetail[];
};

export type PreparationIngredientDetail = {
  food_id: number;
  name: string;
  quantity_g: number;
  preparation_state: string;
  is_condiment: boolean;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type PreparationComponentDetail = PreparationIngredientDetail | {
  preparation_id: number;
  food_id?: null;
  name: string;
  quantity_g: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  calories: number;
};

export type PreparationDetail = {
  id: number;
  name: string;
  is_personal: boolean;
  is_active: boolean;
  version: number;
  household_label: string;
  default_portion_g: number;
  yield_g: number;
  selection_mode: "units" | "grams";
  selected_units: number | null;
  grams: number;
  nutrition: { calories: number; protein_g: number; carbs_g: number; fat_g: number; sodium_mg: number | null };
  allergens: string[];
  allergen_status: string;
  evidence: { source_name?: string; source_url?: string; yield_evidence?: string; preparation_notes?: string };
  ingredients: PreparationComponentDetail[];
  recipe_ingredients: { food_id: number; name: string; quantity_g: number }[];
};
