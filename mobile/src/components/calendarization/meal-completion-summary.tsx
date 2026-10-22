import type { PropsWithChildren } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Check, CheckCheck } from "lucide-react-native";

import type { MealExecutionItem } from "@/api/types";
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

export function MealCompletionSurface({ children }: PropsWithChildren) {
  return <View style={styles.surface}>{children}</View>;
}

export function DailyMealCompletionCard({ mealKeys, mealExecution, mealNutrition }: { mealKeys: (string | null | undefined)[]; mealExecution?: MealExecutionItem[] | null; mealNutrition: MealCompletionNutrition[] }) {
  const completedKeys = new Set(normalizeMealExecution(mealExecution).filter((item) => item.status === "completed").map((item) => item.meal_key));
  const completedCount = mealKeys.filter((key) => key != null && completedKeys.has(key)).length;
  const nutrition = mealNutrition.reduce((total, meal) => meal.key != null && completedKeys.has(meal.key) ? {
    calories: total.calories + meal.calories,
    carbsGrams: total.carbsGrams + meal.carbsGrams,
    fatGrams: total.fatGrams + meal.fatGrams,
    proteinGrams: total.proteinGrams + meal.proteinGrams,
  } : total, { calories: 0, carbsGrams: 0, fatGrams: 0, proteinGrams: 0 });
  return (
    <MealCompletionSurface>
      <View accessibilityLabel={`Cumplimiento comidas: ${completedCount} de ${mealKeys.length} completadas`} accessible style={styles.row}>
        <View style={styles.completionIcon}>
          <CheckCheck color={tokens.color.entityIconForeground} size={16} strokeWidth={2.2} />
        </View>
        <Text style={styles.label}>Cumplimiento comidas</Text>
        <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={styles.checks}>
          {mealKeys.map((key, index) => {
            const completed = key != null && completedKeys.has(key);
            return (
              <View key={key ?? `meal-${index}`} style={[styles.checkCircle, completed ? styles.checkCircleCompleted : styles.checkCirclePending]}>
                <Check color={completed ? tokens.color.entityIconForeground : tokens.color.textMuted} size={14} strokeWidth={3} />
              </View>
            );
          })}
        </View>
      </View>
      <Text style={styles.nutritionSummary}>
        <Text style={styles.nutritionSummaryValue}>{rounded(nutrition.calories)}</Text>
        {"kcal   P:"}<Text style={styles.nutritionSummaryValue}>{rounded(nutrition.proteinGrams)}</Text>
        {"g   C:"}<Text style={styles.nutritionSummaryValue}>{rounded(nutrition.carbsGrams)}</Text>
        {"g   G:"}<Text style={styles.nutritionSummaryValue}>{rounded(nutrition.fatGrams)}</Text>{"g"}
      </Text>
    </MealCompletionSurface>
  );
}

const styles = StyleSheet.create({
  checkCircle: { alignItems: "center", borderRadius: tokens.radius.pill, height: 22, justifyContent: "center", width: 22 },
  checkCircleCompleted: { backgroundColor: tokens.color.meal },
  checkCirclePending: { backgroundColor: tokens.color.borderDefault },
  checks: { alignItems: "center", flexDirection: "row", flexShrink: 1, flexWrap: "wrap", gap: tokens.spacing.xs, justifyContent: "flex-end" },
  completionIcon: { alignItems: "center", backgroundColor: tokens.color.meal, borderRadius: tokens.radius.sm, height: 22, justifyContent: "center", width: 22 },
  label: { color: tokens.color.textMain, flex: 1, fontSize: 15, fontWeight: tokens.weight.bold, minWidth: 0 },
  nutritionSummary: { alignSelf: "flex-end", color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: "300", lineHeight: 16, marginTop: -16, paddingBottom: tokens.spacing.md, textAlign: "right" },
  nutritionSummaryValue: { fontWeight: tokens.weight.semibold },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  surface: { backgroundColor: `${tokens.color.meal}1A`, borderColor: `${tokens.color.meal}B3`, borderRadius: tokens.radius.lg + 4, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 54, paddingHorizontal: 14 },
});
