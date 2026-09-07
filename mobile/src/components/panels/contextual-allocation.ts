export type MacroGramValues = {
  proteinGrams: number;
  carbsGrams: number;
  fatGrams: number;
};

export type ContextualMacroAllocation = {
  protein: number;
  carbs: number;
  fat: number;
};

function validGrams(value: number): number {
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function percentage(part: number, total: number): number {
  return total > 0 ? part / total * 100 : 0;
}

/**
 * Returns each row's contribution to the visible context, independently for
 * protein, carbohydrates and fat. Each non-empty macro column totals 100%.
 */
export function contextualMacroAllocations(items: MacroGramValues[]): ContextualMacroAllocation[] {
  const totals = items.reduce(
    (sum, item) => ({
      protein: sum.protein + validGrams(item.proteinGrams),
      carbs: sum.carbs + validGrams(item.carbsGrams),
      fat: sum.fat + validGrams(item.fatGrams),
    }),
    { protein: 0, carbs: 0, fat: 0 },
  );

  return items.map((item) => ({
    protein: percentage(validGrams(item.proteinGrams), totals.protein),
    carbs: percentage(validGrams(item.carbsGrams), totals.carbs),
    fat: percentage(validGrams(item.fatGrams), totals.fat),
  }));
}
