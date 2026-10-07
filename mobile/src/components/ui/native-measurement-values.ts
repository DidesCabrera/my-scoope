export const HEIGHT_VALUES = Array.from({ length: 171 }, (_, index) => 80 + index);
export const WEIGHT_KILOGRAM_VALUES = Array.from({ length: 326 }, (_, index) => 25 + index);
export const WEIGHT_GRAM_VALUES = Array.from({ length: 10 }, (_, index) => index * 100);

export function heightFromValue(value: string): number {
  const parsed = Math.round(Number(value));
  return Number.isFinite(parsed) ? Math.min(250, Math.max(80, parsed)) : 170;
}

export function weightPartsFromValue(value: string): { grams: number; kilograms: number } {
  const parsed = Number(value.replace(",", "."));
  const bounded = Number.isFinite(parsed) ? Math.min(350, Math.max(25, parsed)) : 70;
  const tenths = Math.round(bounded * 10);
  const kilograms = Math.floor(tenths / 10);
  return { grams: (tenths % 10) * 100, kilograms };
}

export function weightValueFromParts(kilograms: number, grams: number): string {
  if (kilograms >= 350) return "350";
  return String(kilograms + grams / 1000);
}
