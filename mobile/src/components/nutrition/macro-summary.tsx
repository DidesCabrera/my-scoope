import { StyleSheet, Text, View } from "react-native";

import type { MacroTotals } from "@/api/types";
import { NutritionMetric } from "@/components/nutrition/nutrition-metric";
import { tokens } from "@/design/tokens";

function value(value?: number | null): string {
  return Math.round(value ?? 0).toString();
}

export function MacroSummary({ totals }: { totals?: MacroTotals }) {
  const macros = [
    { label: "Proteína", value: value(totals?.protein_g), color: tokens.color.protein },
    { label: "Carbos", value: value(totals?.carbs_g), color: tokens.color.carbs },
    { label: "Grasas", value: value(totals?.fat_g), color: tokens.color.fat },
  ];
  return (
    <View style={styles.row}>
      <View style={styles.kcal}>
        <Text style={styles.kcalValue}>{value(totals?.total_kcal)}</Text>
        <Text style={styles.kcalLabel}>kcal</Text>
      </View>
      <View style={styles.macros}>
        {macros.map((macro) => (
          <NutritionMetric color={macro.color} key={macro.label} label={macro.label} unit="g" value={macro.value} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: "stretch", flexDirection: "row", gap: tokens.spacing.md },
  kcal: { alignItems: "center", backgroundColor: tokens.color.kcalSurface, borderColor: tokens.color.kcalBorder, borderRadius: tokens.radius.card, borderWidth: 2, justifyContent: "center", minHeight: 102, width: 102 },
  kcalValue: { color: tokens.color.textMain, fontSize: 29, fontWeight: "800" },
  kcalLabel: { color: tokens.color.textMuted, fontSize: 12, fontWeight: "700" },
  macros: { flex: 1, justifyContent: "center" },
});
