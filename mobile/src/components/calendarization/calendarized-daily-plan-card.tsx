import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";

import type { DailyPlanSnapshot } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels } from "@/components/panels";
import { EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { snapshotAllocation, snapshotCalories, snapshotMealPanelItem } from "./presentation-adapters";

type Props = { dayId: number | null; eyebrow: string; planName?: string; snapshot: DailyPlanSnapshot };

export function CalendarizedDailyPlanCard({ dayId, eyebrow, planName, snapshot }: Props) {
  const router = useRouter();
  const meals = snapshot.meals ?? [];
  const totals = snapshot.totals;
  const totalCalories = snapshotCalories(totals);
  const mealItems = meals.map((meal, index) => snapshotMealPanelItem(meal, index, totalCalories));
  return (
    <NutritionEntityCard
      actions={dayId ? <EntityCardAction label="Ir al detalle del plan calendarizado" onPress={() => router.push(`/program/days/${dayId}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} /></EntityCardAction> : null}
      entity="dailyPlan"
      eyebrow={eyebrow}
      indicators={[{ icon: "meal", label: "comidas", value: meals.length }]}
      kpiVariant="nested"
      nutrition={{
        calories: totalCalories,
        carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
        fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
        protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: null },
      }}
      title={snapshot.name ?? planName ?? "Plan diario"}>
      <MealPanels
        items={mealItems}
        onOpenItem={(meal) => {
          if (meal.detailId == null) return;
          const context = dayId != null
            ? `?calendarizedDayId=${dayId}&mealKey=${encodeURIComponent(meal.id)}`
            : "";
          router.push(`/libraries/meals/${meal.detailId}${context}` as Href);
        }}
      />
    </NutritionEntityCard>
  );
}
