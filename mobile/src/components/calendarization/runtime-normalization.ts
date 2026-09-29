import type {
  ActiveProgramData,
  ActiveProgramDay,
  CalendarizationData,
  CalendarizedDayDetail,
  DailyPlanSnapshot,
  LibraryWeekPanelItem,
  MealSnapshot,
} from "@/api/types";

function record(value: unknown): Record<string, unknown> | null {
  return value != null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function positiveInteger(value: unknown, fallback: number): number {
  return Number.isInteger(value) && Number(value) > 0 ? Number(value) : fallback;
}

function normalizeCalendarization(value: unknown): CalendarizationData | null {
  const candidate = record(value);
  if (!candidate || !Number.isInteger(candidate.id)) return null;
  const status = candidate.status;
  if (status !== "scheduled" && status !== "active" && status !== "paused" && status !== "completed" && status !== "cancelled") return null;
  return {
    id: Number(candidate.id),
    source_program_id: Number.isInteger(candidate.source_program_id) ? Number(candidate.source_program_id) : null,
    program_name: text(candidate.program_name, "Programa activo"),
    status,
    start_date: text(candidate.start_date),
    end_date: text(candidate.end_date),
    timezone_name: text(candidate.timezone_name, "UTC"),
    progress_day: finiteNumber(candidate.progress_day),
    progress_total_days: finiteNumber(candidate.progress_total_days),
    progress_percent: finiteNumber(candidate.progress_percent),
  };
}

function normalizeActiveDay(value: unknown): ActiveProgramDay | null {
  const candidate = record(value);
  if (!candidate || !Number.isInteger(candidate.id) || typeof candidate.calendar_date !== "string") return null;
  return {
    id: Number(candidate.id),
    calendar_date: candidate.calendar_date,
    week_number: positiveInteger(candidate.week_number, 1),
    day_number: positiveInteger(candidate.day_number, 1),
    has_plan: candidate.has_plan === true,
    plan_name: text(candidate.plan_name),
  };
}

function normalizeWeek(value: unknown): LibraryWeekPanelItem | null {
  const candidate = record(value);
  if (!candidate) return null;
  return {
    id: text(candidate.id, `week-${positiveInteger(candidate.week_number, 1)}`),
    week_number: positiveInteger(candidate.week_number, 1),
    days: (Array.isArray(candidate.days) ? candidate.days : []) as LibraryWeekPanelItem["days"],
    foods: Array.isArray(candidate.foods) ? candidate.foods : [],
    calories: finiteNumber(candidate.calories),
    calorie_share: finiteNumber(candidate.calorie_share),
    calorie_distribution: record(candidate.calorie_distribution) as LibraryWeekPanelItem["calorie_distribution"] ?? { protein: 0, carbs: 0, fat: 0 },
    protein_grams: finiteNumber(candidate.protein_grams),
    carbs_grams: finiteNumber(candidate.carbs_grams),
    fat_grams: finiteNumber(candidate.fat_grams),
    protein_allocation: finiteNumber(candidate.protein_allocation),
    carbs_allocation: finiteNumber(candidate.carbs_allocation),
    fat_allocation: finiteNumber(candidate.fat_allocation),
    filled_days_count: finiteNumber(candidate.filled_days_count),
    meals_count: finiteNumber(candidate.meals_count),
    foods_count: finiteNumber(candidate.foods_count),
    average_calories: finiteNumber(candidate.average_calories),
  };
}

export function normalizeActiveProgramData(value: unknown): ActiveProgramData {
  const candidate = record(value) ?? {};
  const days = (Array.isArray(candidate.days) ? candidate.days : [])
    .map(normalizeActiveDay)
    .filter((day): day is ActiveProgramDay => day != null);
  const weeks = (Array.isArray(candidate.weeks) ? candidate.weeks : [])
    .map(normalizeWeek)
    .filter((week): week is LibraryWeekPanelItem => week != null);
  const indicators: ActiveProgramData["indicators"] = (Array.isArray(candidate.indicators) ? candidate.indicators : []).flatMap((value) => {
    const indicator = record(value);
    if (!indicator || (indicator.icon !== "food" && indicator.icon !== "dailyPlan" && indicator.icon !== "week")) return [];
    const icon: ActiveProgramData["indicators"][number]["icon"] = indicator.icon;
    return [{
      icon,
      label: text(indicator.label),
      value: typeof indicator.value === "string" ? indicator.value : finiteNumber(indicator.value),
    }];
  });
  return {
    calendarization: normalizeCalendarization(candidate.calendarization),
    weeks_count: finiteNumber(candidate.weeks_count, weeks.length),
    weeks,
    days,
    adherence: record(candidate.adherence) as ActiveProgramData["adherence"],
    indicators,
  };
}

function normalizeMeal(value: unknown): MealSnapshot | null {
  const candidate = record(value);
  if (!candidate) return null;
  const totals = record(candidate.totals);
  return {
    key: typeof candidate.key === "string" ? candidate.key : undefined,
    detail_id: Number.isInteger(candidate.detail_id) ? Number(candidate.detail_id) : null,
    name: text(candidate.name, "Comida"),
    hour: typeof candidate.hour === "string" ? candidate.hour : null,
    note: text(candidate.note),
    totals: totals ?? undefined,
    foods: (Array.isArray(candidate.foods) ? candidate.foods : [])
      .filter((food) => record(food) != null) as MealSnapshot["foods"],
  };
}

export function normalizeDailyPlanSnapshot(value: unknown): DailyPlanSnapshot | null {
  const candidate = record(value);
  if (!candidate) return null;
  return {
    ...candidate,
    name: text(candidate.name),
    totals: record(candidate.totals) ?? undefined,
    meals: (Array.isArray(candidate.meals) ? candidate.meals : [])
      .map(normalizeMeal)
      .filter((meal): meal is MealSnapshot => meal != null),
  };
}

export function normalizeCalendarizedDayDetail(value: unknown): CalendarizedDayDetail | null {
  const day = normalizeActiveDay(value);
  const candidate = record(value);
  if (!day || !candidate) return null;
  return {
    ...day,
    meal_execution: Array.isArray(candidate.meal_execution) ? candidate.meal_execution : [],
    plan_snapshot: normalizeDailyPlanSnapshot(candidate.plan_snapshot),
  };
}
