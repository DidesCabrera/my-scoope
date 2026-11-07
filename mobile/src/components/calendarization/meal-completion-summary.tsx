import { type PropsWithChildren, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Check, CheckCheck } from "lucide-react-native";

import type { MealExecutionItem, SupplementIntake } from "@/api/types";
import { tokens } from "@/design/tokens";
import { normalizeMealExecution } from "./meal-execution";

type MealCompletionNutrition = {
  calories: number;
  carbsGrams: number;
  fatGrams: number;
  key: string | null | undefined;
  proteinGrams: number;
};

function rounded(value: number): string {
  return Number.isFinite(value) ? Math.round(value).toString() : "0";
}

export function MealCompletionSurface({ children, color = tokens.color.meal }: PropsWithChildren<{ color?: string }>) {
  return <View style={[styles.surface, { backgroundColor: `${color}1A`, borderColor: `${color}B3` }]}>{children}</View>;
}

function CompletionSummaryRow({ accessibilityLabel, color, completed, keys, label }: { accessibilityLabel: string; color: string; completed: boolean[]; keys: string[]; label: string }) {
  return (
    <View accessibilityLabel={accessibilityLabel} accessible style={styles.row}>
      <View style={[styles.completionIcon, { backgroundColor: color }]}>
        <CheckCheck color={tokens.color.entityIconForeground} size={16} strokeWidth={2.2} />
      </View>
      <Text style={styles.label}>{label}</Text>
      <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={styles.checks}>
        {completed.map((isCompleted, index) => (
          <View key={keys[index] ?? `${label}-${index}`} style={[styles.checkCircle, isCompleted ? { backgroundColor: color } : styles.checkCirclePending]}>
            <Check color={isCompleted ? tokens.color.entityIconForeground : tokens.color.textMuted} size={14} strokeWidth={3} />
          </View>
        ))}
      </View>
    </View>
  );
}

export function DailySupplementCompletionCard({ intakes }: { intakes: SupplementIntake[] }) {
  const completed = intakes.map((intake) => intake.status === "completed");
  const completedCount = completed.filter(Boolean).length;
  return (
    <MealCompletionSurface color={tokens.color.supplement}>
      <CompletionSummaryRow
        accessibilityLabel={`Cumplimiento sups: ${completedCount} de ${intakes.length} completadas`}
        color={tokens.color.supplement}
        completed={completed}
        keys={intakes.map((intake) => intake.key)}
        label="Cumplimiento sups"
      />
    </MealCompletionSurface>
  );
}

export function DailyMealCompletionCard({ mealKeys, mealExecution, mealNutrition }: { mealKeys: (string | null | undefined)[]; mealExecution?: MealExecutionItem[] | null; mealNutrition: MealCompletionNutrition[] }) {
  const [metricsWidth, setMetricsWidth] = useState(0);
  const completedKeys = new Set(normalizeMealExecution(mealExecution).filter((item) => item.status === "completed").map((item) => item.meal_key));
  const completedCount = mealKeys.filter((key) => key != null && completedKeys.has(key)).length;
  const nutrition = mealNutrition.reduce((total, meal) => meal.key != null && completedKeys.has(meal.key) ? {
    calories: total.calories + meal.calories,
    carbsGrams: total.carbsGrams + meal.carbsGrams,
    fatGrams: total.fatGrams + meal.fatGrams,
    proteinGrams: total.proteinGrams + meal.proteinGrams,
  } : total, { calories: 0, carbsGrams: 0, fatGrams: 0, proteinGrams: 0 });
  const programmedNutrition = mealNutrition.reduce((total, meal) => ({
    calories: total.calories + meal.calories,
    carbsGrams: total.carbsGrams + meal.carbsGrams,
    fatGrams: total.fatGrams + meal.fatGrams,
    proteinGrams: total.proteinGrams + meal.proteinGrams,
  }), { calories: 0, carbsGrams: 0, fatGrams: 0, proteinGrams: 0 });
  const progressMetrics = [
    { color: tokens.color.kcalBorder, consumed: nutrition.calories, label: "Calorías", programmed: programmedNutrition.calories, unit: "kcal" },
    { color: tokens.color.protein, consumed: nutrition.proteinGrams, label: "Proteína", programmed: programmedNutrition.proteinGrams, unit: "g" },
    { color: tokens.color.carbs, consumed: nutrition.carbsGrams, label: "Carbos", programmed: programmedNutrition.carbsGrams, unit: "g" },
    { color: tokens.color.fat, consumed: nutrition.fatGrams, label: "Grasas", programmed: programmedNutrition.fatGrams, unit: "g" },
  ];
  const metricColumnWidth = Math.max(0, (metricsWidth - 3 * tokens.spacing.sm) / 4);
  return (
    <MealCompletionSurface>
      <CompletionSummaryRow
        accessibilityLabel={`Cumplimiento comidas: ${completedCount} de ${mealKeys.length} completadas`}
        color={tokens.color.meal}
        completed={mealKeys.map((key) => key != null && completedKeys.has(key))}
        keys={mealKeys.map((key, index) => key ?? `meal-${index}`)}
        label="Cumplimiento comidas"
      />
      <View onLayout={({ nativeEvent: { layout } }) => setMetricsWidth((current) => current === layout.width ? current : layout.width)} style={styles.progressMetrics}>
        {progressMetrics.map(({ color, consumed, label, programmed, unit }) => {
          const percentage = programmed > 0 ? Math.min(100, Math.max(0, consumed / programmed * 100)) : 0;
          return <View key={label} style={[styles.progressMetric, { width: metricColumnWidth }]}>
            <View style={styles.progressMetricHeading}>
              <Text numberOfLines={1} style={styles.progressMetricLabel}>{label}</Text>
              <Text numberOfLines={1} style={styles.progressMetricValue}>{rounded(consumed)} {unit}</Text>
            </View>
            <View accessibilityLabel={`${label}: ${rounded(consumed)} de ${rounded(programmed)} ${unit}`} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: percentage }} style={styles.progressTrack}>
              <View style={[styles.progressFill, { backgroundColor: color, width: `${percentage}%` }]} />
            </View>
          </View>;
        })}
      </View>
    </MealCompletionSurface>
  );
}

const styles = StyleSheet.create({
  progressFill: { borderRadius: 999, height: "100%" },
  progressMetric: { gap: 5, minWidth: 0 },
  progressMetricHeading: { gap: 2 },
  progressMetricLabel: { color: tokens.color.textMuted, fontSize: 11 },
  progressMetricValue: { color: tokens.color.textMain, fontSize: 11, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.semibold },
  progressMetrics: { flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: 2, marginTop: -12, paddingBottom: tokens.spacing.md + 4 },
  progressTrack: { backgroundColor: tokens.color.borderDefault, borderRadius: 999, height: 6, overflow: "hidden" },
  checkCircle: { alignItems: "center", borderRadius: tokens.radius.pill, height: 22, justifyContent: "center", width: 22 },
  checkCirclePending: { backgroundColor: tokens.color.borderDefault },
  checks: { alignItems: "center", flexDirection: "row", flexShrink: 1, flexWrap: "wrap", gap: tokens.spacing.xs, justifyContent: "flex-end" },
  completionIcon: { alignItems: "center", borderRadius: tokens.radius.sm, height: 22, justifyContent: "center", width: 22 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: 15, fontWeight: tokens.weight.bold, minWidth: 0 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  surface: { borderRadius: tokens.radius.lg + 4, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 54, paddingHorizontal: 14 },
});
