import type { PropsWithChildren } from "react";
import { StyleSheet, Text, View } from "react-native";
import { Check } from "lucide-react-native";

import type { MealExecutionItem } from "@/api/types";
import { tokens } from "@/design/tokens";

export function MealCompletionSurface({ children }: PropsWithChildren) {
  return <View style={styles.surface}>{children}</View>;
}

export function DailyMealCompletionCard({ mealKeys, mealExecution }: { mealKeys: (string | null | undefined)[]; mealExecution: MealExecutionItem[] }) {
  const completedKeys = new Set(mealExecution.filter((item) => item.status === "completed").map((item) => item.meal_key));
  const completedCount = mealKeys.filter((key) => key != null && completedKeys.has(key)).length;
  return (
    <MealCompletionSurface>
      <View accessibilityLabel={`Cumplimiento comidas: ${completedCount} de ${mealKeys.length} completadas`} accessible style={styles.row}>
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
    </MealCompletionSurface>
  );
}

const styles = StyleSheet.create({
  checkCircle: { alignItems: "center", borderRadius: tokens.radius.pill, height: 22, justifyContent: "center", width: 22 },
  checkCircleCompleted: { backgroundColor: tokens.color.meal },
  checkCirclePending: { backgroundColor: tokens.color.borderDefault },
  checks: { alignItems: "center", flexDirection: "row", flexShrink: 1, flexWrap: "wrap", gap: tokens.spacing.xs, justifyContent: "flex-end" },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold, minWidth: 0 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  surface: { backgroundColor: `${tokens.color.meal}1A`, borderColor: tokens.color.meal, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 54, paddingHorizontal: tokens.card.outerPadding },
});
