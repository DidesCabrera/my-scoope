export function validCalendarFoodPeriod(start: string, end: string): boolean {
  if (!start || !end || end < start) return false;
  const startTime = Date.parse(`${start}T12:00:00Z`);
  const endTime = Date.parse(`${end}T12:00:00Z`);
  return Number.isFinite(startTime) && Number.isFinite(endTime) && endTime - startTime < 366 * 86_400_000;
}

export function selectCalendarFoodDate(start: string, end: string, day: string): { start: string; end: string; tooLong: boolean } {
  if (!start || end || day < start) return { start: day, end: "", tooLong: false };
  if (!validCalendarFoodPeriod(start, day)) return { start, end: "", tooLong: true };
  return { start, end: day, tooLong: false };
}

export function calendarFoodDayRole(day: string, start: string, end: string): "start" | "end" | "single" | "between" | null {
  if (day === start && day === end) return "single";
  if (day === start) return "start";
  if (day === end) return "end";
  return start && end && day > start && day < end ? "between" : null;
}
