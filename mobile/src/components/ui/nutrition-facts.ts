export type NutritionFacts = {
  proteinG: number | null;
  totalFatG: number | null;
  saturatedFatG: number | null;
  carbsG: number | null;
  sugarG: number | null;
  fiberG: number | null;
  sodiumMg: number | null;
};

export type NutritionFactRow = {
  emphasized: boolean;
  id: keyof NutritionFacts;
  label: string;
  per100Value: string;
  portionValue: string;
};

export function formatNutritionFact(value: number | null, unit: "g" | "mg"): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString("es-CL", { maximumFractionDigits: 1 })} ${unit}`;
}

export function formatNutritionPortion(value: number | null, unit: "g" | "ml"): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString("es-CL", { maximumFractionDigits: 1 })} ${unit}`;
}

export function formatNutritionFactForPortion(value: number | null, portionQuantity: number | null, unit: "g" | "mg"): string {
  if (value == null || portionQuantity == null || !Number.isFinite(value) || !Number.isFinite(portionQuantity)) return "-";
  return formatNutritionFact(value * portionQuantity / 100, unit);
}

export function nutritionFactRows(facts: NutritionFacts, portionQuantity: number | null): NutritionFactRow[] {
  const row = (id: keyof NutritionFacts, label: string, unit: "g" | "mg", emphasized: boolean): NutritionFactRow => ({
    emphasized,
    id,
    label,
    per100Value: formatNutritionFact(facts[id], unit),
    portionValue: formatNutritionFactForPortion(facts[id], portionQuantity, unit),
  });
  return [
    row("proteinG", "Proteínas", "g", true),
    row("totalFatG", "Grasas totales", "g", true),
    row("saturatedFatG", "Grasas saturadas", "g", false),
    row("carbsG", "Carbohidratos", "g", true),
    row("sugarG", "Azúcares", "g", false),
    row("fiberG", "Fibra", "g", false),
    row("sodiumMg", "Sodio", "mg", false),
  ];
}
