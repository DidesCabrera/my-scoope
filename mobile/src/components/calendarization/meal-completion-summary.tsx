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
          {mealKeys.map((key, index) => (
            <Check
              color={key != null && completedKeys.has(key) ? tokens.color.meal : tokens.color.textSubtle}
              key={key ?? `meal-${index}`}
              size={18}
              strokeWidth={2.8}
            />
          ))}
        </View>
      </View>
    </MealCompletionSurface>
  );
}

const styles = StyleSheet.create({
  checks: { alignItems: "center", flexDirection: "row", flexShrink: 1, flexWrap: "wrap", gap: 2, justifyContent: "flex-end" },
  label: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, minWidth: 0 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minHeight: 52 },
  surface: { backgroundColor: `${tokens.color.meal}1A`, borderColor: tokens.color.meal, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 54, paddingHorizontal: tokens.card.outerPadding },
});
