import { type Href, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { useState } from "react";

import type { DailyPlanSnapshot, MealExecutionItem } from "@/api/types";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels, type MealPanelEditing, type MealPanelItem } from "@/components/panels";
import { Button, EntityCardAction } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { snapshotCalories, snapshotMacroDistribution, snapshotMealPanelItem } from "./presentation-adapters";
import { DailyMealCompletionCard } from "./meal-completion-summary";
import { normalizeMealExecution } from "./meal-execution";
import { CalendarizedEntityActions } from "./calendarized-entity-actions";

type Props = {
  dayId: number | null;
  dateLabel: string;
  eyebrow: string;
  mealExecution?: MealExecutionItem[] | null;
  editing?: MealPanelEditing;
  onChangeMealTime?: (meal: MealPanelItem, hour: string) => Promise<void>;
  onAddMeal?: () => void;
  planName?: string;
  position?: { dayNumber: number; weekNumber: number };
  snapshot: DailyPlanSnapshot;
};

export function CalendarizedDailyPlanCard({ dayId, dateLabel, editing, eyebrow, mealExecution = [], onAddMeal, onChangeMealTime, planName, position, snapshot }: Props) {
  const router = useRouter();
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const meals = snapshot.meals ?? [];
  const totals = snapshot.totals;
  const totalCalories = snapshotCalories(totals);
  const mealKeys = new Set(meals.flatMap((meal) => meal.key ? [meal.key] : []));
  const normalizedMealExecution = normalizeMealExecution(mealExecution);
  const executions = normalizedMealExecution.filter((item) => mealKeys.has(item.meal_key));
  const completedMealKeys = new Set(executions.filter((item) => item.status === "completed").map((item) => item.meal_key));
  const mealItems = meals.map((meal, index) => ({
    ...snapshotMealPanelItem(meal, index, totals),
    completed: Boolean(meal.key && completedMealKeys.has(meal.key)),
  }));
  const cardEditing = editing && onChangeMealTime ? { ...editing, onChangeTime: setTimeChangeMeal } : editing;
  return (<>
    <NutritionEntityCard
      actions={dayId ? <EntityCardAction label="Ir al detalle del plan calendarizado" onPress={() => router.push(`/program/days/${dayId}` as Href)} role="link"><ChevronRight color={tokens.color.textMuted} size={21} /></EntityCardAction> : null}
      beforeNutrition={<DailyMealCompletionCard mealExecution={mealExecution} mealKeys={meals.map((meal) => meal.key)} />}
      completion={{ noteCount: executions.filter((item) => item.note.trim()).length }}
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
        editing={cardEditing}
        items={mealItems}
        nestedScroll={false}
        showEditTab={false}
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
    <CalendarizedEntityActions
      entityName={timeChangeMeal?.name ?? "Comida"}
      initialAction="change-time"
      key={timeChangeMeal?.id ?? "closed-card-time-change"}
      onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }}
      timeChange={timeChangeMeal && onChangeMealTime ? { initialTime: timeChangeMeal.time, onSubmit: (hour) => onChangeMealTime(timeChangeMeal, hour) } : undefined}
      visible={timeChangeMeal != null}
    />
  </>);
}

const styles = StyleSheet.create({
  addMealAction: { marginTop: tokens.spacing.md },
});
