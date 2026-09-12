export type ShareNutrition = {
  calories: number;
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
};

export type ShareMealSnapshot = {
  name: string;
  time?: string | null;
  nutrition: ShareNutrition;
  foods: { name: string; quantity_grams: number; nutrition: ShareNutrition }[];
};

export type ShareSnapshot = {
  schema_version: string;
  subject: { type: "daily_plan" | "food" | "meal" | "program"; title: string; variant?: string };
  summary: {
    basis_grams?: number;
    duration_weeks?: number;
    filled_days?: number;
    meal_count?: number;
    food_count?: number;
  };
  nutrition: ShareNutrition;
  foods?: { name: string; quantity_grams: number; nutrition: ShareNutrition }[];
  meals?: ShareMealSnapshot[];
  days?: { week_number: number; day_number: number; plan: ShareSnapshot }[];
};

export type ShareResource = {
  id: string;
  subject_type: "daily_plan" | "food" | "meal" | "program";
  title: string;
  public_url?: string;
  claim_policy: "none" | "single" | "multiple";
  status?: "active" | "revoked" | "expired";
  created_at?: string;
  snapshot?: ShareSnapshot;
};

export type ShareClaimResult = { resource_id: string; inbox_item_id: number };

export type SharingInboxItem = {
  id: number;
  resource_id: string;
  subject_type: ShareResource["subject_type"];
  title: string;
  sender: string;
  public_url: string;
  is_read: boolean;
  is_favorite: boolean;
  is_saved: boolean;
  created_at: string;
};

export type SharingInboxData = { items: SharingInboxItem[]; count: number };
