export function foodNutritionBasisLabel(value: string): string | null {
  const metric = value.match(/([\d.,]+)\s*(g|ml)\b/i);
  if (!metric) return null;
  return `Información nutricional: ${metric[1]} ${metric[2].toLowerCase()}`;
}
