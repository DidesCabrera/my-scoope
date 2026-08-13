import type { MacroTotals } from "@/api/types";
import { NutritionKpiSection } from "@/components/nutrition/nutrition-kpi-section";

function value(value?: number | null): string {
  return Math.round(value ?? 0).toString();
}

function numeric(value?: number | null): number {
  return Number.isFinite(value ?? Number.NaN) ? Number(value) : 0;
}

function allocation(parts: { protein: number; carbs: number; fat: number }) {
  const proteinKcal = parts.protein * 4;
  const carbsKcal = parts.carbs * 4;
  const fatKcal = parts.fat * 9;
  const total = proteinKcal + carbsKcal + fatKcal;
  if (total <= 0) {
    return { protein: 0, carbs: 0, fat: 0 };
  }
  return {
    protein: (proteinKcal / total) * 100,
    carbs: (carbsKcal / total) * 100,
    fat: (fatKcal / total) * 100,
  };
}

export function MacroSummary({ totals }: { totals?: MacroTotals }) {
  const protein = numeric(totals?.protein_g);
  const carbs = numeric(totals?.carbs_g);
  const fat = numeric(totals?.fat_g);
  const shares = allocation({ protein, carbs, fat });
  return (
    <NutritionKpiSection
      calories={Number(value(totals?.total_kcal))}
      carbs={{ grams: carbs, allocation: shares.carbs }}
      fat={{ grams: fat, allocation: shares.fat }}
      protein={{ grams: protein, allocation: shares.protein }}
    />
  );
}
