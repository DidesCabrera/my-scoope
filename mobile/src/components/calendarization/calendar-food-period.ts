export function validCalendarFoodPeriod(start: string, end: string): boolean {
  if (!start || !end || end < start) return false;
  const startTime = Date.parse(`${start}T12:00:00Z`);
  const endTime = Date.parse(`${end}T12:00:00Z`);
  return Number.isFinite(startTime) && Number.isFinite(endTime) && endTime - startTime < 366 * 86_400_000;
}
