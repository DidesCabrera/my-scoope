import type { PickerKind } from "./composition-picker-screen";

type PickerPayloadInput = {
  contextDailyPlanId?: number;
  contextDailyPlanMealId?: number;
  dayNumbers: number[];
  hour: string;
  kind: PickerKind;
  note: string;
  quantity: string;
  relationId?: number;
  relationKey?: string;
  selectedId: number;
  weekNumber: number;
};

export function buildCompositionPickerPayload({
  contextDailyPlanId,
  contextDailyPlanMealId,
  dayNumbers,
  hour,
  kind,
  note,
  quantity,
  relationId,
  relationKey,
  selectedId,
  weekNumber,
}: PickerPayloadInput) {
  if (kind === "food-to-meal") return {
    food_id: selectedId,
    meal_food_id: relationId,
    dailyplan_id: contextDailyPlanId,
    dailyplan_meal_id: contextDailyPlanMealId,
    quantity: Number(quantity),
  };
  if (kind === "food-to-calendarized-meal") return {
    food_id: selectedId,
    food_snapshot_key: relationKey,
    quantity: Number(quantity),
  };
  if (kind === "meal-to-dailyplan") return {
    meal_id: selectedId,
    dailyplan_meal_id: relationId,
    hour,
    note,
  };
  if (kind === "meal-to-calendarized-day") return {
    meal_id: selectedId,
    meal_snapshot_key: relationKey,
    hour,
    note,
  };
  if (kind === "dailyplan-to-calendarized-day") return { dailyplan_id: selectedId };
  return { dailyplan_id: selectedId, week_number: weekNumber, day_numbers: dayNumbers };
}
