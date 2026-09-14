import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";

import type { DailyPlanSnapshot, MealExecutionItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels } from "@/components/panels";
import { Button, EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { snapshotCalories, snapshotMacroDistribution, snapshotMealPanelItem } from "./presentation-adapters";
import { DailyMealCompletionCard } from "./meal-completion-summary";

type Props = {
  dayId: number | null;
  dateLabel: string;
  eyebrow: string;
  mealExecution?: MealExecutionItem[];
  onAddMeal?: () => void;
  planName?: string;
  position?: { dayNumber: number; weekNumber: number };
  snapshot: DailyPlanSnapshot;
};

export function CalendarizedDailyPlanCard({ dayId, dateLabel, eyebrow, mealExecution = [], onAddMeal, planName, position, snapshot }: Props) {
  const router = useRouter();
  const meals = snapshot.meals ?? [];
  const totals = snapshot.totals;
  const totalCalories = snapshotCalories(totals);
  const mealKeys = new Set(meals.flatMap((meal) => meal.key ? [meal.key] : []));
  const executions = mealExecution.filter((item) => mealKeys.has(item.meal_key));
  const completedMealKeys = new Set(executions.filter((item) => item.status === "completed").map((item) => item.meal_key));
  const mealItems = meals.map((meal, index) => ({
    ...snapshotMealPanelItem(meal, index, totals),
    completed: Boolean(meal.key && completedMealKeys.has(meal.key)),
  }));
  return (
    <NutritionEntityCard
      actions={dayId ? <EntityCardAction label="Ir al detalle del plan calendarizado" onPress={() => router.push(`/program/days/${dayId}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} /></EntityCardAction> : null}
      beforeNutrition={<DailyMealCompletionCard mealExecution={mealExecution} mealKeys={meals.map((meal) => meal.key)} />}
      completion={{ completedCount: executions.filter((item) => item.status === "completed").length, noteCount: executions.filter((item) => item.note.trim()).length }}
      entity="dailyPlan"
      eyebrow={eyebrow}
      indicators={[
        ...(position ? [{ icon: "day" as const, label: "posición", value: `S${position.weekNumber} · D${position.dayNumber}` }] : []),
        { icon: "meal", label: "comidas", value: meals.length },
        { icon: "day", iconPosition: "leading", label: "fecha", tone: "surfaceMuted", value: dateLabel },
      ]}
      nutrition={{
        calories: totalCalories,
        carbs: { allocation: snapshotMacroDistribution(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
        fat: { allocation: snapshotMacroDistribution(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
        protein: { allocation: snapshotMacroDistribution(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
      }}
      title={snapshot.name ?? planName ?? "Plan diario"}>
      <MealPanels
        items={mealItems}
        onOpenItem={(meal) => {
          if (dayId == null || !meal.id) return;
          router.push({
            pathname: "/program/days/[id]/meals/[mealKey]",
            params: { id: String(dayId), mealKey: meal.id },
          } as Href);
        }}
      />
      {onAddMeal ? <View style={styles.addMealAction}><Button bleed label="+ Agregar Comida" onPress={onAddMeal} /></View> : null}
    </NutritionEntityCard>
  );
}

const styles = StyleSheet.create({
  addMealAction: { marginTop: tokens.spacing.md },
});
