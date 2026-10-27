export function monthKeyFromDate(value: string): string {
  return value.slice(0, 7);
}

export function isCurrentMonthFromToday(date: string, today: string | null | undefined): boolean {
  return Boolean(today && date >= today && monthKeyFromDate(date) === monthKeyFromDate(today));
}

export function shiftMonth(monthKey: string, delta: number): string {
  const year = Number(monthKey.slice(0, 4));
  const month = Number(monthKey.slice(5, 7)) - 1;
  return new Date(Date.UTC(year, month + delta, 1)).toISOString().slice(0, 7);
}

export function monthWindow(monthKey: string): { startDate: string; days: number } {
  const year = Number(monthKey.slice(0, 4));
  const month = Number(monthKey.slice(5, 7)) - 1;
  const first = new Date(Date.UTC(year, month, 1));
  const leadingDays = (first.getUTCDay() + 6) % 7;
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const startDate = new Date(Date.UTC(year, month, 1 - leadingDays)).toISOString().slice(0, 10);
  return { startDate, days: Math.ceil((leadingDays + daysInMonth) / 7) * 7 };
}

export function monthLabel(monthKey: string): string {
  const value = new Intl.DateTimeFormat("es-CL", { month: "long", timeZone: "UTC", year: "numeric" })
    .format(new Date(`${monthKey}-01T12:00:00Z`));
  return value.charAt(0).toUpperCase() + value.slice(1);
}
