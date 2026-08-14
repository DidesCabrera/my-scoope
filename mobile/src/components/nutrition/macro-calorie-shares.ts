export type MacroCalorieValues = {
  carbsGrams: number;
  fatGrams: number;
  proteinGrams: number;
};

function normalizedGrams(value: number): number {
  return Number.isFinite(value) ? Math.max(0, value) : 0;
}

export function macroCalorieShares({ carbsGrams, fatGrams, proteinGrams }: MacroCalorieValues) {
  const proteinCalories = normalizedGrams(proteinGrams) * 4;
  const carbsCalories = normalizedGrams(carbsGrams) * 4;
  const fatCalories = normalizedGrams(fatGrams) * 9;
  const total = proteinCalories + carbsCalories + fatCalories;

  if (total === 0) return { protein: 0, carbs: 0, fat: 0 };

  const exact = [proteinCalories, carbsCalories, fatCalories].map((value) => (value / total) * 100);
  const shares = exact.map(Math.floor);
  const remainder = 100 - shares.reduce((sum, value) => sum + value, 0);
  const priority = exact
    .map((value, index) => ({ fraction: value - shares[index], index }))
    .sort((left, right) => right.fraction - left.fraction);
  for (let index = 0; index < remainder; index += 1) shares[priority[index].index] += 1;

  return { protein: shares[0], carbs: shares[1], fat: shares[2] };
}
