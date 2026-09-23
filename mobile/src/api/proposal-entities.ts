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
  days: { week_number: number; day_number: number; dailyplan: ProposalDailyPlan }[];
};
