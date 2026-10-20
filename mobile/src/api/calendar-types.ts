import type { DailyPlanSnapshot, MealExecutionItem } from "./types";

export type ActiveProgramDay = {
  id: number;
  calendar_date: string;
  week_number: number;
  day_number: number;
  has_plan: boolean;
  plan_name: string;
};

export type CalendarDay = {
  id: number | null;
  calendar_date: string;
  has_plan: boolean;
  plan_name: string;
  source_kind: "program" | "manual" | null;
  source_program_name: string | null;
  has_execution: boolean;
};

export type CalendarOverviewData = {
  local_date: string;
  start_date: string;
  end_date: string;
  days: CalendarDay[];
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
