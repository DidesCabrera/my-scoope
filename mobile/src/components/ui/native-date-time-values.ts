export type DateTimePickerMode = "date" | "time";

export function pickerDateFromValue(value: string, mode: DateTimePickerMode, fallback = new Date()): Date {
  const date = new Date(fallback);
  if (mode === "time") {
    const match = /^(\d{2}):(\d{2})/.exec(value);
    if (!match) return date;
    date.setHours(Number(match[1]), Number(match[2]), 0, 0);
    return date;
  }

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return date;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12);
}

export function pickerValueFromDate(date: Date, mode: DateTimePickerMode): string {
  if (mode === "time") {
    return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
