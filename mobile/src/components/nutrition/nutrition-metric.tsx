import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function NutritionMetric({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number | string;
  unit: string;
  color: string;
}) {
  return (
    <View style={styles.metric}>
      <View style={[styles.marker, { backgroundColor: color }]} />
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value} <Text style={styles.unit}>{unit}</Text></Text>
    </View>
  );
}

const styles = StyleSheet.create({
  metric: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, minHeight: 34 },
  marker: { borderRadius: tokens.radius.pill, height: 8, width: 8 },
  label: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  value: { color: tokens.color.textMain, fontSize: 14, fontWeight: "800", fontVariant: ["tabular-nums"] },
  unit: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "700" },
});
