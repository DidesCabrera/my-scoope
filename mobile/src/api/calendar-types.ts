import type { DailyPlanSnapshot, LibraryFoodPanelItem, MealExecutionItem } from "./types";

export type ActiveProgramDay = {
  id: number;
  calendar_date: string;
  week_number: number;
  day_number: number;
  has_plan: boolean;
  plan_name: string;
};

export type CalendarCommitmentKind = "shopping" | "cooking" | "training";

export type CalendarCommitment = {
  id: number;
  calendar_date: string;
  kind: CalendarCommitmentKind;
  note: string;
  food_period_start: string | null;
  food_period_end: string | null;
  food_plans_count: number;
  foods: LibraryFoodPanelItem[];
};

export type CalendarPeriodFoodsData = {
  start_date: string;
  end_date: string;
  plans_count: number;
  meals_count?: number;
  foods: LibraryFoodPanelItem[];
};

export type CalendarDay = {
  id: number | null;
  calendar_date: string;
  has_plan: boolean;
  plan_name: string;
  plan_calories?: number | null;
  plan_protein_grams?: number | null;
  plan_carbs_grams?: number | null;
  plan_fat_grams?: number | null;
  plan_protein_per_kilogram?: number | null;
  source_kind: "program" | "manual" | null;
  source_program_name: string | null;
  has_execution: boolean;
  commitments?: CalendarCommitment[];
};

export type CalendarOverviewData = {
  local_date: string;
  start_date: string;
  end_date: string;
  days: CalendarDay[];
  future_plans_count?: number;
  last_scheduled_date?: string | null;
};

export type CalendarDayDetailData = CalendarDay & {
  plan_snapshot: DailyPlanSnapshot | null;
  meal_execution: MealExecutionItem[];
};

export type CalendarDayHistoryData = {
  calendar_date: string;
  items: {
    id: number;
    plan_name: string;
    source_kind: "program" | "manual";
    source_program_name: string | null;
    assignment_state: "current" | "empty" | "superseded" | "removed";
    created_at: string;
    state_changed_at: string | null;
    change_reason: string;
    superseded_by_id: number | null;
    execution_events: number;
  }[];
};

export type CalendarProgressData = {
  period_id: number | null;
  period_start: string;
  period_end: string;
  days_with_plan: number;
  scheduled_meals: number;
  elapsed_meals: number;
  completed_meals: number;
  skipped_meals: number;
  unrecorded_meals: number;
  adherence_percent: number;
};
