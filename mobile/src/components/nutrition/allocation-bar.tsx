import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

export type AllocationTone = "protein" | "carbs" | "fat" | "calories";

type AllocationBarProps = {
  value: number;
  tone: AllocationTone;
  accessibilityLabel?: string;
  displayValue?: number | string;
  size?: "compact" | "regular";
  style?: StyleProp<ViewStyle>;
};

const toneLabels: Record<AllocationTone, string> = {
  protein: "Proteína",
  carbs: "Carbos",
  fat: "Grasas",
  calories: "Calorías",
};

function toneColor(tone: AllocationTone): string {
  return tone === "calories" ? tokens.color.kcalBorder : tokens.color[tone];
}

function normalizedPercentage(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(value, 100));
}

function progressAccessibility(value: number, tone: AllocationTone, accessibilityLabel?: string) {
  return {
    accessibilityLabel: accessibilityLabel ?? `${toneLabels[tone]}: ${Math.round(value)}%`,
    accessibilityRole: "progressbar" as const,
    accessibilityValue: { min: 0, max: 100, now: value },
  };
}

export function KpiAllocationBar({
  value,
  tone,
  accessibilityLabel,
  size = "regular",
  style,
}: AllocationBarProps) {
  const normalized = normalizedPercentage(value);
  const color = toneColor(tone);
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.kpiContainer, size === "compact" && styles.kpiContainerCompact, style]}>
      <View style={[styles.fill, { backgroundColor: color, width: `${normalized}%` }]} />
      <Text style={styles.panelPercentage}>{Math.round(normalized)}%</Text>
    </View>
  );
}

export function PanelAllocationBar({
  value,
  tone,
  accessibilityLabel,
  displayValue,
  size = "regular",
  style,
}: AllocationBarProps) {
  const normalized = normalizedPercentage(value);
  const color = toneColor(tone);
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.panelTrack, size === "compact" && styles.panelTrackCompact, style]}>
      <View style={[styles.fill, { backgroundColor: color, width: `${normalized}%` }]} />
      <Text style={styles.panelPercentage}>{displayValue ?? `${Math.round(normalized)}%`}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { bottom: 0, left: 0, position: "absolute", top: 0 },
  kpiContainer: { backgroundColor: tokens.color.allocationBarTrack, borderRadius: 6, height: 24, justifyContent: "center", minWidth: 0, overflow: "hidden", width: "100%" },
  kpiContainerCompact: { height: 18 },
  panelTrack: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: 4, height: 24, justifyContent: "center", overflow: "hidden", width: "100%" },
  panelTrackCompact: { height: 18 },
  panelPercentage: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, fontVariant: ["tabular-nums"], letterSpacing: 0, paddingRight: tokens.spacing.xs, textAlign: "right" },
});
