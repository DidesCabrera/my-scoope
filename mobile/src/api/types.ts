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
  review_disclosure_required: boolean;
  review_disclosure_version: string;
};

export type AccountDeletionData = { receipt_id: string };

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
  meal_execution: MealExecutionItem[];
  adherence: AdherenceSummary | null;
  measurements: MeasurementSummary | null;
  reminders: ReminderSettings | null;
  pending_revision: CalendarizationRevision | null;
};

export type MealExecutionStatus = "planned" | "completed" | "skipped";

export type MealExecutionItem = {
  meal_key: string;
  status: MealExecutionStatus;
  last_event_id: number | null;
  recorded_at: string | null;
  note: string;
};

export type AdherenceSummary = {
  period_start: string;
  period_end: string;
  days: number;
  days_with_plan: number;
  planned_meals: number;
  completed_meals: number;
  skipped_meals: number;
  unrecorded_meals: number;
  adherence_percent: number;
};

export type MeasurementSummary = {
  items: { weight_log_id: number; measured_on: string; weight_kg: number }[];
  count: number;
  first_weight_kg: number | null;
  latest_weight_kg: number | null;
  change_kg: number | null;
};

export type ReminderSettings = {
  timezone_name: string;
  daily_notification_time: string;
  daily_notifications_enabled: boolean;
  meal_notifications_enabled: boolean;
  upcoming: {
    event_key: string;
    event_type: "daily_plan" | "meal_reminder";
    meal_key: string;
    local_date: string;
    local_time: string;
    scheduled_for_utc: string;
    status: string;
  }[];
};

export type ApplePushRegistration = {
  delivery_mode: "apns" | "local";
  token_fingerprint: string;
  environment: "sandbox" | "production";
  is_active: boolean;
};

export type CalendarizationRevision = {
  id: number;
  effective_from: string;
  status: "pending" | "applied" | "rejected";
  rationale: string;
  days: {
    calendar_date: string;
    before_name: string;
    after_name: string;
    before_totals: MacroTotals;
    after_totals: MacroTotals;
  }[];
  created_at: string;
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
  calendarization_id?: number | null;
};

export type WeightListData = { items: WeightItem[]; count: number };

export type OnboardingInput = {
  birth_date: string;
  sex: string;
  height_cm: number;
  weight_kg: number;
};

export type WeightInput = { weight_kg: number; measured_on?: string };

export type FoodLabelCaptureInput = {
  name: string;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  saturated_fat_g?: number;
  sugar_g?: number;
  fiber_g?: number;
  sodium_mg?: number;
  serving_size_g?: number;
  declared_energy_kcal_per_100g?: number;
  detected_basis: "per_100g" | "per_serving" | "manual";
  ocr_engine: string;
  ocr_engine_version: string;
  field_confidence: Record<string, number>;
  warnings: string[];
  idempotency_key: string;
};

export type FoodLabelCaptureResult = {
  id: number;
  name: string;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  saturated_fat_g: number | null;
  sugar_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  total_kcal: number;
  is_user_food: boolean;
  is_verified: boolean;
  capture_receipt_id: number;
  detected_basis: string;
  serving_size_g: number | null;
  ocr_engine: string;
  created_at: string;
};

export type MealCheckInInput = {
  action: "completed" | "skipped" | "reset";
  idempotency_key: string;
  note?: string;
};

export type ReviewInput = {
  period_start: string;
  period_end: string;
  idempotency_key: string;
  energy_score: number;
  hunger_score: number;
  training_performance_score: number;
  note?: string;
};

export type CalendarizationReview = {
  id: number;
  period_start: string;
  period_end: string;
  energy_score: number | null;
  hunger_score: number | null;
  training_performance_score: number | null;
  note: string;
  summary_snapshot: {
    schema_version: string;
    adherence: AdherenceSummary;
    measurements: MeasurementSummary;
  };
  created_at: string;
};

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

export type SubscriptionData = {
  eligible: boolean;
  purchases_enabled: boolean;
  app_account_token: string;
  plan_name: string;
  status: string;
  products: {
    product_id: string;
    plan_name: string;
    interval: "month" | "year" | string;
  }[];
  evidence: {
    provider: string;
    status: string;
    period_end: string | null;
  }[];
  duplicate_active_providers: boolean;
};
