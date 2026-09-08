export type CurrentWeekDay = {
  date: string;
  dayOfMonth: number;
  isToday: boolean;
  label: string;
  monthLabel: string;
};

export type CalendarizedWeekDayPreference = {
  calendar_date: string;
  day_number: number;
  id: number;
  week_number: number;
};

const weekdayLabels = ["L", "M", "X", "J", "V", "S", "D"] as const;

function parseLocalDate(value: string): Date {
  return new Date(`${value}T12:00:00`);
}

export function compactDateLabel(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" })
    .format(parseLocalDate(value))
    .replace(/\.$/, "");
}

export function compactMonthLabel(value: string): string {
  const label = new Intl.DateTimeFormat("es-CL", { month: "short" })
    .format(parseLocalDate(value))
    .replace(/\.$/, "")
    .slice(0, 3);
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`;
}

export function homePlanDateLabel(value: string): string {
  const date = parseLocalDate(value);
  const weekday = new Intl.DateTimeFormat("es-CL", { weekday: "long" }).format(date);
  return `${weekday} ${date.getDate()} de ${compactMonthLabel(value).toLocaleLowerCase("es-CL")}`;
}

export function preferredCalendarizedDay<T extends CalendarizedWeekDayPreference>(
  days: T[],
  weekNumber: number,
  today: string,
): T | undefined {
  const weekDays = days
    .filter((day) => day.week_number === weekNumber)
    .sort((left, right) => left.calendar_date.localeCompare(right.calendar_date));
  return weekDays.find((day) => day.calendar_date === today)
    ?? weekDays.find((day) => day.day_number === 1)
    ?? weekDays[0];
}

function dateValue(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function currentWeekDays(localDate: string): CurrentWeekDay[] {
  const today = parseLocalDate(localDate);
  const mondayOffset = (today.getDay() + 6) % 7;
  const monday = new Date(today);
  monday.setDate(today.getDate() - mondayOffset);

  return weekdayLabels.map((label, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    const value = dateValue(date);
    return { date: value, dayOfMonth: date.getDate(), isToday: value === localDate, label, monthLabel: compactMonthLabel(value) };
  });
}

export function currentWeekRange(localDate: string): string {
  const days = currentWeekDays(localDate);
  return `${compactDateLabel(days[0].date)} — ${compactDateLabel(days[6].date)}`;
}
