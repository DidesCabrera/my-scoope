import { StyleSheet, Text, View } from "react-native";

import { ProgressBar } from "@/components/ui";
import { tokens } from "@/design/tokens";

export function NutrientProgress({
  label,
  value,
  target,
  unit = "g",
  color,
}: {
  label: string;
  value: number;
  target: number;
  unit?: string;
  color: string;
}) {
  const progress = target > 0 ? Math.round((value / target) * 100) : 0;
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.value}>{Math.round(value)} / {Math.round(target)} {unit}</Text>
      </View>
      <ProgressBar color={color} value={progress} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: tokens.spacing.sm },
  header: { alignItems: "baseline", flexDirection: "row", justifyContent: "space-between" },
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: "700" },
  value: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "800", fontVariant: ["tabular-nums"] },
});
