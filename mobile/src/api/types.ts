export type ApiErrorDetail = {
  code: string;
  message: string;
  details: Record<string, unknown>;
};

export type ApiEnvelope<T> =
  | { ok: true; data: T; error: null }
  | { ok: false; data: Record<string, never>; error: ApiErrorDetail };

export type SessionData = {
  user_id: number;
  username: string;
  email: string;
  display_name: string;
  scopes: string[];
  device_session_id: string | null;
};

export type ProfileData = {
  birth_date: string | null;
  sex: string;
  height_cm: number | null;
  timezone_name: string;
  onboarding_completed: boolean;
  onboarding_version: number;
  current_weight_kg: number | null;
};

export type CalendarizationData = {
  id: number;
  program_name: string;
  status: string;
  start_date: string;
  end_date: string;
  timezone_name: string;
  progress_day: number;
  progress_total_days: number;
  progress_percent: number;
};

export type TodayData = {
  local_date: string;
  calendarization: CalendarizationData | null;
  day_id: number | null;
  has_plan: boolean;
  plan_snapshot: DailyPlanSnapshot | null;
};

export type DailyPlanSnapshot = {
  schema_version?: string;
  name?: string;
  totals?: MacroTotals;
  meals?: MealSnapshot[];
  [key: string]: unknown;
};

export type MacroTotals = {
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  total_kcal?: number | null;
};

export type MealSnapshot = {
  key?: string;
  name?: string;
  hour?: string | null;
  note?: string;
  totals?: MacroTotals;
  foods?: { key?: string; name?: string; quantity_g?: number | null }[];
};

export type WeightItem = {
  id: number;
  measured_on: string;
  weight_kg: number;
  source: string;
  created_at: string;
};

export type WeightListData = { items: WeightItem[]; count: number };

export type OnboardingInput = {
  birth_date: string;
  sex: string;
  height_cm: number;
  weight_kg: number;
};

export type WeightInput = { weight_kg: number; measured_on?: string };

export type OAuthTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
  refresh_expires_in: number;
  scope: string;
  device_session_id: string;
};

export type OAuthErrorResponse = {
  error?: string;
  error_description?: string;
  details?: { code?: string; [key: string]: unknown };
};
