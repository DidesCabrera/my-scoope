export type DateTimeDraft = {
  day: number;
  hour: number;
  minute: number;
  month: number;
  year: number;
};

export function dateTimeDraftFromDate(date: Date): DateTimeDraft {
  return {
    day: date.getDate(),
    hour: date.getHours(),
    minute: date.getMinutes(),
    month: date.getMonth(),
    year: date.getFullYear(),
  };
}

export function committedDateTimeDraft(
  draft: DateTimeDraft,
  mode: "date" | "time",
  base: Date,
  minimum: Date,
  maximum: Date,
): Date {
  let updated: Date;
  if (mode === "time") {
    updated = new Date(base);
    updated.setHours(draft.hour, draft.minute, 0, 0);
  } else {
    const lastDay = new Date(draft.year, draft.month + 1, 0).getDate();
    updated = new Date(draft.year, draft.month, Math.min(draft.day, lastDay));
  }
  return updated < minimum ? new Date(minimum) : updated > maximum ? new Date(maximum) : updated;
}
