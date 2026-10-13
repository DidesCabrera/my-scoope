export const DEFAULT_MEAL_TIME = "00:00";

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

export function initialMealTime(value?: string | null): string {
  const time = value?.slice(0, 5) ?? "";
  return TIME_PATTERN.test(time) ? time : DEFAULT_MEAL_TIME;
}

export function isValidMealTime(value: string): boolean {
  return TIME_PATTERN.test(value);
}
