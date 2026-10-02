const compactMonthLabels = [
  "ene.", "feb.", "mar.", "abr.", "may.", "jun.",
  "jul.", "ago.", "sep.", "oct.", "nov.", "dic.",
] as const;

export function formatCompactDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return `${date.getDate()} ${compactMonthLabels[date.getMonth()]} ${date.getFullYear()}`;
}
