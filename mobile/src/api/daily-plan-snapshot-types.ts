import type { MacroTotals, MealSnapshot } from "./types";
import type { SupplementIntake } from "./supplement-types";

export type DailyPlanSnapshot = {
  schema_version?: string;
  source?: {
    dailyplan_id?: number | null;
    program_day_id?: number | null;
  };
  name?: string;
  totals?: MacroTotals;
  meals?: MealSnapshot[];
  supplement_intakes?: SupplementIntake[];
  [key: string]: unknown;
};
