export const supplementForms = [
  "capsule", "tablet", "softgel", "gummy", "sachet", "powder", "liquid", "drop",
  "scoop", "ml", "g", "mg", "mcg", "iu", "tsp",
] as const;

export function defaultUnitForSupplementForm(form: string): string {
  if (form === "powder") return "g";
  if (form === "liquid") return "ml";
  return form;
}

export function editableSupplementForm(form: string, defaultUnit: string): string {
  return defaultUnit && defaultUnitForSupplementForm(form) !== defaultUnit ? defaultUnit : form;
}
