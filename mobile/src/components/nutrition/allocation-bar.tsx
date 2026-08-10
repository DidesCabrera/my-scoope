import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

export type AllocationTone = "protein" | "carbs" | "fat";

type AllocationBarProps = {
  value: number;
  tone: AllocationTone;
  accessibilityLabel?: string;
  size?: "compact" | "regular";
  style?: StyleProp<ViewStyle>;
};

const toneLabels: Record<AllocationTone, string> = {
  protein: "Proteína",
  carbs: "Carbos",
  fat: "Grasas",
};

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
  const color = tokens.color[tone];
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.kpiContainer, size === "compact" && styles.kpiContainerCompact, style]}>
      <View style={[styles.kpiPercentage, size === "compact" && styles.kpiPercentageCompact, { backgroundColor: color }]}>
        <Text style={[styles.kpiPercentageText, size === "compact" && styles.kpiPercentageTextCompact]}>{Math.round(normalized)}%</Text>
      </View>
      <View style={styles.kpiTrack}>
        <View style={[styles.fill, { backgroundColor: color, width: `${normalized}%` }]} />
      </View>
    </View>
  );
}

export function PanelAllocationBar({
  value,
  tone,
  accessibilityLabel,
  size = "regular",
  style,
}: AllocationBarProps) {
  const normalized = normalizedPercentage(value);
  const color = tokens.color[tone];
  return (
    <View
      {...progressAccessibility(normalized, tone, accessibilityLabel)}
      style={[styles.panelTrack, size === "compact" && styles.panelTrackCompact, style]}>
      <View style={[styles.fill, { backgroundColor: color, width: `${normalized}%` }]} />
      <Text style={styles.panelPercentage}>{Math.round(normalized)}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { bottom: 0, left: 0, position: "absolute", top: 0 },
  kpiContainer: { flexDirection: "row", height: 24, minWidth: 0, overflow: "hidden", width: "100%" },
  kpiContainerCompact: { height: 18 },
  kpiPercentage: { alignItems: "center", borderBottomLeftRadius: 6, borderRightColor: "rgba(0, 0, 0, 0.18)", borderRightWidth: 1, borderTopLeftRadius: 6, justifyContent: "center", paddingHorizontal: tokens.spacing.xs, width: 48 },
  kpiPercentageCompact: { paddingHorizontal: 2, width: 42 },
  kpiPercentageText: { color: "#000000", fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, fontVariant: ["tabular-nums"] },
  kpiPercentageTextCompact: { fontSize: tokens.type.label },
  kpiTrack: { backgroundColor: tokens.color.allocationBarTrack, borderBottomRightRadius: 6, borderTopRightRadius: 6, flex: 1, minWidth: 0, overflow: "hidden" },
  panelTrack: { backgroundColor: tokens.color.allocationPanelTrack, borderRadius: 4, height: 24, justifyContent: "center", overflow: "hidden", width: "100%" },
  panelTrackCompact: { height: 18 },
  panelPercentage: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, fontVariant: ["tabular-nums"], paddingRight: tokens.spacing.xs, textAlign: "right" },
});
