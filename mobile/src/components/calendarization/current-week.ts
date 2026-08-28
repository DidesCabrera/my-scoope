export type CurrentWeekDay = {
  date: string;
  dayOfMonth: number;
  isToday: boolean;
  label: string;
};

const weekdayLabels = ["L", "M", "X", "J", "V", "S", "D"] as const;

function parseLocalDate(value: string): Date {
  return new Date(`${value}T12:00:00`);
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
    return { date: value, dayOfMonth: date.getDate(), isToday: value === localDate, label };
  });
}

export function currentWeekRange(localDate: string): string {
  const days = currentWeekDays(localDate);
  const first = parseLocalDate(days[0].date);
  const last = parseLocalDate(days[6].date);
  const formatter = new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short" });
  return `${formatter.format(first)} — ${formatter.format(last)}`;
}
