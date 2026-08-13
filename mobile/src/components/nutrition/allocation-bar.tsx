import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

export type AllocationTone = "protein" | "carbs" | "fat" | "calories" | "ppk";

type AllocationBarProps = {
  value: number;
  tone: AllocationTone;
  accessibilityLabel?: string;
  displayValue?: number | string;
  showValue?: boolean;
  size?: "compact" | "regular";
  textSize?: 12 | 13;
  style?: StyleProp<ViewStyle>;
};

const toneLabels: Record<AllocationTone, string> = {
  protein: "Proteina",
  carbs: "Carbos",
  fat: "Grasas",
  calories: "Calorias",
  ppk: "PPK",
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
  textSize = 13,
  style,
}: AllocationBarProps) {
  const normalized = normalizedPercentage(value);
  const color = toneColor(tone);
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.kpiContainer, size === "compact" && styles.kpiContainerCompact, style]}>
      <View style={[styles.fill, styles.kpiFill, { backgroundColor: color, width: `${normalized}%` }]} />
      <Text style={[styles.panelPercentage, { fontSize: textSize }]}>{Math.round(normalized)}%</Text>
    </View>
  );
}

export function PanelAllocationBar({
  value,
  tone,
  accessibilityLabel,
  displayValue,
  showValue = true,
  size = "regular",
  textSize = 13,
  style,
}: AllocationBarProps) {
  const normalized = normalizedPercentage(value);
  const color = toneColor(tone);
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.panelTrack, size === "compact" && styles.panelTrackCompact, style]}>
      <View style={[styles.fill, styles.panelFill, { backgroundColor: color, width: `${normalized}%` }]} />
      {showValue ? <Text style={[styles.panelPercentage, { fontSize: textSize }]}>{displayValue ?? `${Math.round(normalized)}%`}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { bottom: 0, left: 0, position: "absolute", top: 0 },
  kpiFill: { borderRadius: 6 },
  kpiContainer: { backgroundColor: tokens.color.allocationBarTrack, borderRadius: 6, height: 24, justifyContent: "center", minWidth: 0, overflow: "hidden", width: "100%" },
  kpiContainerCompact: { height: 18 },
  panelTrack: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: 4, height: 24, justifyContent: "center", overflow: "hidden", width: "100%" },
  panelFill: { borderRadius: 4 },
  panelTrackCompact: { height: 18 },
  panelPercentage: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "500", fontVariant: ["tabular-nums"], letterSpacing: 0, paddingRight: tokens.spacing.xs, textAlign: "right" },
});
