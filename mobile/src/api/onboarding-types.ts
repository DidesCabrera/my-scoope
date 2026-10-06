export type OnboardingStage = "intro" | "profile" | "summary" | "plan" | "plans" | "completed";

export type OnboardingInput = {
  birth_date: string;
  sex: string;
  height_cm: number;
  weight_kg: number;
};
export type OnboardingAnalyzeInput = OnboardingInput & {
  goal: string;
  activity_level: string;
  training_frequency: number;
  dietary_pattern: string;
  allergies_or_intolerances: string[];
  avoided_foods: string[];
};

export type OnboardingEstimate = {
  total_kcal: number;
  protein: number;
  carbs: number;
  fat: number;
  weight_kg: number;
  estimated_bmr: number | null;
  estimated_tdee: number | null;
  estimated_maintenance_kcal: number | null;
  protein_per_kg: number;
  macro_distribution: Record<string, number>;
};

export type OnboardingStateData = {
  stage: OnboardingStage;
  birth_date: string | null;
  sex: string;
  height_cm: number | null;
  weight_kg: number | null;
  goal: string;
  activity_level: string;
  training_frequency: number | null;
  dietary_pattern: string;
  allergies_or_intolerances: string[];
  avoided_foods: string[];
  estimate: OnboardingEstimate | null;
  proposal_id: number | null;
};
