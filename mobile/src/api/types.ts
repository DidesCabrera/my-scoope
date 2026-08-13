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
  status: CalendarizationStatus;
  start_date: string;
  end_date: string;
  timezone_name: string;
  progress_day: number;
  progress_total_days: number;
  progress_percent: number;
};

export type CalendarizationStatus = "scheduled" | "active" | "paused" | "completed" | "cancelled";

export type ActiveProgramDay = {
  id: number;
  calendar_date: string;
  week_number: number;
  day_number: number;
  has_plan: boolean;
  plan_name: string;
};

export type ActiveProgramData = {
  calendarization: CalendarizationData | null;
  days: ActiveProgramDay[];
};

export type CalendarizationActivationInput = {
  program_id: number;
  start_date: string;
  timezone_name: string;
  daily_notification_time: string;
  daily_notifications_enabled: boolean;
  meal_notifications_enabled: boolean;
  confirm_incomplete: boolean;
  replace_current: boolean;
};

export type CalendarizationActivationData = ActiveProgramData & {
  empty_dates: string[];
  replaced_calendarization_id: number | null;
};

export type CalendarizationHistoryItem = {
  id: number;
  program_name: string;
  status: CalendarizationStatus;
  start_date: string;
  end_date: string;
  timezone_name: string;
  days_total: number;
  days_with_plan: number;
  created_at: string;
};

export type CalendarizationHistoryData = {
  items: CalendarizationHistoryItem[];
  count: number;
};

export type CalendarizedDayDetail = ActiveProgramDay & {
  plan_snapshot: DailyPlanSnapshot | null;
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

export type LibraryEntity = "food" | "meal" | "dailyPlan" | "program";

export type LibraryNutrition = {
  calories: number;
  protein: { grams: number; allocation: number; per_kilogram: number | null };
  carbs: { grams: number; allocation: number };
  fat: { grams: number; allocation: number };
};

export type LibraryIndicator = {
  icon?: "day" | "food" | "meal" | "dailyPlan" | "week";
  label: string;
  value: number | string;
};

export type LibraryFoodPanelItem = {
  id: string;
  name: string;
  quantity: number;
  quantity_unit: string;
  calories: number;
  calorie_share: number;
  calorie_distribution: LibraryCalorieDistribution;
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
  protein_allocation: number;
  carbs_allocation: number;
  fat_allocation: number;
};

export type LibraryMealPanelItem = {
  id: string;
  detail_id: number;
  name: string;
  time: string | null;
  foods: LibraryFoodPanelItem[];
  calories: number;
  calorie_share: number;
  calorie_distribution: LibraryCalorieDistribution;
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
  protein_allocation: number;
  carbs_allocation: number;
  fat_allocation: number;
};

export type LibraryWeekPanelItem = {
  id: string;
  week_number: number;
  days: { day_label: string; plan_name: string | null }[];
  calories: number;
  calorie_share: number;
  calorie_distribution: LibraryCalorieDistribution;
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
  protein_allocation: number;
  carbs_allocation: number;
  fat_allocation: number;
};

export type LibraryCalorieDistribution = {
  protein: number;
  carbs: number;
  fat: number;
};

export type LibraryPanel = {
  kind: "none" | "foods" | "meals" | "weeks";
  foods: LibraryFoodPanelItem[];
  meals: LibraryMealPanelItem[];
  weeks: LibraryWeekPanelItem[];
};

export type LibraryItem = {
  id: number;
  entity: LibraryEntity;
  name: string;
  subtitle: string;
  nutrition: LibraryNutrition;
  indicators: LibraryIndicator[];
  panel: LibraryPanel;
  creator: string;
  created_at: string;
  can_calendarize: boolean;
};

export type LibraryPageData = {
  items: LibraryItem[];
  total: number;
  offset: number;
  limit: number;
  search: string | null;
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

export type MobilePageData<T> = {
  items: T[];
  total: number;
  offset: number;
  limit: number;
};

export type MobileAction = {
  key: string;
  label: string;
  tone: "default" | "warning" | "danger";
  requires_confirmation: boolean;
};

export type ProposalStatus = "draft" | "pending_review" | "approved" | "rejected" | "cancelled" | "applied";

export type ProposalSummary = {
  id: number;
  title: string;
  summary: string;
  status: ProposalStatus;
  status_label: string;
  source: string;
  attachment_kind: "meal" | "dailyplan" | "brief";
  attachment_label: string;
  attachment_name: string;
  is_reviewable: boolean;
  created_at: string | null;
  actions: MobileAction[];
};

export type ProposalListData = MobilePageData<ProposalSummary> & {
  pending_count: number;
};

export type ProposalFact = {
  label: string;
  value: string;
};

export type ProposalKpis = {
  total_kcal: number | null;
  protein: number | null;
  carbs: number | null;
  fat: number | null;
  ppk: number | null;
};

export type ProposalFood = {
  food_id: number | null;
  food_name: string;
  quantity: number | null;
  unit: string;
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

export type ProposalDetail = ProposalSummary & {
  dailyplan_id: number | null;
  dailyplan_name: string;
  created_by_username: string;
  reviewed_by_username: string | null;
  intent: string | null;
  entity_title: string;
  target_facts: ProposalFact[];
  current_facts: ProposalFact[];
  validation_facts: ProposalFact[];
  meal: ProposalMeal | null;
  dailyplan: ProposalDailyPlan | null;
  subject_context_warning: {
    requires_warning: boolean;
    source_label: string;
    calculation_weight_label: string;
    title: string;
    message: string;
  };
  applied_result: {
    kind: "meal" | "dailyplan" | null;
    object_id: number | null;
    object_name: string;
  } | null;
  applied_at: string | null;
};

export type ComparisonKind = "foods" | "meals" | "dailyplans";

export type ComparisonSelection = {
  id: number;
  quantity?: number | null;
};

export type ComparisonKindOption = {
  key: ComparisonKind;
  label: string;
  entity_label: string;
  uses_quantity: boolean;
  quantity_unit: string | null;
  includes_ppk: boolean;
};

export type ComparisonMetadata = { kinds: ComparisonKindOption[] };

export type ComparisonOption = { id: number; name: string };

export type ComparisonOptionsData = MobilePageData<ComparisonOption> & { search: string | null };

export type ComparisonMetricValues = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  protein_per_kilogram: number | null;
};

export type ComparisonResultItem = {
  position: number;
  id: number;
  name: string;
  quantity: number | null;
  values: ComparisonMetricValues;
};

export type ComparisonMetricBar = {
  position: number;
  id: number;
  label: string;
  quantity: number | null;
  value: number;
  formatted_value: string;
  relative_percentage: number;
};

export type ComparisonMetric = {
  key: "total_kcal" | "ppk" | "protein" | "carbs" | "fat" | "alloc_protein" | "alloc_carbs" | "alloc_fat";
  label: string;
  unit: string;
  bars: ComparisonMetricBar[];
};

export type ComparisonResult = {
  kind: ComparisonKind;
  kind_label: string;
  historical_snapshot: boolean;
  saved_comparison_id: number | null;
  saved_comparison_name: string;
  metrics: ComparisonMetric[];
  items: ComparisonResultItem[];
};

export type SavedComparisonSummary = {
  id: number;
  name: string;
  kind: ComparisonKind;
  kind_label: string;
  item_count: number;
  updated_at: string;
};

export type SavedComparisonListData = MobilePageData<SavedComparisonSummary>;

export type SavedComparisonDetail = ComparisonResult & {
  editable_selections: ComparisonSelection[];
  updated_at: string;
};

export type AIJobAcceptedData = {
  job_id: string;
  status: "queued" | "running" | "retrying";
  retry_after_ms: number;
};

export type AITurnResultData = {
  chat_id: number;
  conversation_updated: true;
  has_iteration_warning: boolean;
};

export type AssistantAvailability = {
  is_available: boolean;
  label: string;
  queue_available: boolean;
  available_credits: number;
  monthly_credit_limit: number;
  daily_credit_limit: number;
  max_message_chars: number;
};

export type AIPendingTurn = {
  job_id: string;
  status: "queued" | "running" | "retrying";
  retry_after_ms: number;
};

export type AIChatCardItem = {
  key: string;
  label: string;
  value: string;
  is_pending: boolean;
};

type AIChatDraftCard = {
  type: "profile_draft" | "preference_draft" | "proposal_preferences";
  title: string;
  subtitle: string;
  items: AIChatCardItem[];
  status: string;
};

type AIChatProposalCard = {
  type: "proposal_review";
  proposal_id: number;
  title: string;
  summary: string;
  status: string;
};

type AIChatComparisonCard = {
  type: "saved_comparison";
  comparison_id: number;
  kind: ComparisonKind;
  title: string;
};

type AIChatPreparedActionCard = {
  type: "prepared_action";
  action_id: string;
  title: string;
  summary: string;
  expires_at: string;
  status: "prepared" | "committed" | "cancelled" | "expired" | "failed";
  destructive: boolean;
};

type AIChatGeneratedPlanCard = {
  type: "generated_plan";
  proposal_id: number | null;
  title: string;
  summary: string;
  is_current: boolean;
  items: AIChatCardItem[];
};

export type AIPreparedActionResult = {
  action_id: string;
  status: "committed" | "cancelled";
  refresh_chat: boolean;
};

export type AIChatCard =
  | AIChatDraftCard
  | AIChatProposalCard
  | AIChatComparisonCard
  | AIChatPreparedActionCard
  | AIChatGeneratedPlanCard;

export type AIChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  cards?: AIChatCard[];
  created_at: string | null;
  has_structured_content: boolean;
};

export type AIChatSummary = {
  id: number;
  title: string;
  status: string;
  status_label: string;
  last_message_preview: string;
  message_count: number;
  proposal_id: number | null;
  updated_at: string;
};

export type AIChatListData = MobilePageData<AIChatSummary> & {
  availability: AssistantAvailability;
  pending_new_turn: AIPendingTurn | null;
};

export type AIChatDetail = AIChatSummary & {
  messages: AIChatMessage[];
  availability: AssistantAvailability;
  pending_turn: AIPendingTurn | null;
};
