import { StyleSheet, Text, View } from "react-native";

import type { MacroTotals } from "@/api/types";
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
          <View key={macro.label} style={styles.macroRow}>
            <View style={[styles.dot, { backgroundColor: macro.color }]} />
            <Text style={styles.macroLabel}>{macro.label}</Text>
            <Text style={styles.macroValue}>{macro.value} g</Text>
          </View>
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
  macroRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: 8, minHeight: 32 },
  dot: { borderRadius: 4, height: 8, width: 8 },
  macroLabel: { color: tokens.color.textMuted, flex: 1, fontSize: 13 },
  macroValue: { color: tokens.color.textMain, fontSize: 14, fontWeight: "800", fontVariant: ["tabular-nums"] },
});
