import type { CalendarDay } from "@/api/calendar-types";

export type CalendarWeekGroup = {
  days: CalendarDay[];
  key: string;
  weekNumber: number;
  weekYear: number;
};

function isoWeek(dateValue: string): { weekNumber: number; weekYear: number } {
  const date = new Date(`${dateValue}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const weekYear = date.getUTCFullYear();
  const yearStart = new Date(Date.UTC(weekYear, 0, 1));
  const weekNumber = Math.ceil((((date.getTime() - yearStart.getTime()) / 86_400_000) + 1) / 7);
  return { weekNumber, weekYear };
}

export function groupCalendarDaysByIsoWeek(days: CalendarDay[]): CalendarWeekGroup[] {
  const groups: CalendarWeekGroup[] = [];
  for (const day of days) {
    const { weekNumber, weekYear } = isoWeek(day.calendar_date);
    const key = `${weekYear}-${weekNumber}`;
    const current = groups.at(-1);
    if (current?.key === key) current.days.push(day);
    else groups.push({ days: [day], key, weekNumber, weekYear });
  }
  return groups;
}

export function calendarWeekRangeLabel(days: CalendarDay[]): string {
  const format = (value: string) => new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
  return days.length ? `${format(days[0].calendar_date)} – ${format(days.at(-1)!.calendar_date)}` : "";
}
