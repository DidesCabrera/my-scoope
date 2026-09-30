export type ProposalKpis = {
  total_kcal: number | null;
  protein: number | null;
  carbs: number | null;
  fat: number | null;
  ppk: number | null;
  alloc_protein: number | null;
  alloc_carbs: number | null;
  alloc_fat: number | null;
};

export type ProposalFood = {
  food_id: number | null;
  food_name: string;
  quantity: number | null;
  unit: string;
  protein: number | null;
  carbs: number | null;
  fat: number | null;
  total_kcal: number | null;
};

export type ProposalMeal = {
  name: string;
  foods: ProposalFood[];
  kpis: ProposalKpis | null;
};

export type ProposalDailyPlan = {
  name: string;
  meals: { hour: string | null; note: string; meal: ProposalMeal }[];
  kpis: ProposalKpis | null;
};

export type ProposalProgram = {
  name: string;
  duration_weeks: number;
  warnings: string[];
  nutrition_specification?: {
    version: number;
    duration_weeks: number;
    meals_per_day: number;
    weight_basis: "measured" | "projected";
    measured_weight_kg: number;
    protein_min_ppk: number;
    protein_max_ppk: number;
    fat_max_percent: number;
    calorie_tolerance_percent: number;
    weeks: { week: number; kcal: number; projected_weight_kg: number | null;
      reference_weight_kg: number; protein_min_g: number; protein_max_g: number }[];
  } | null;
  days: { week_number: number; day_number: number; dailyplan: ProposalDailyPlan }[];
};
