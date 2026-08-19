import type { PropsWithChildren } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { Brand, Screen } from "./layout";

export function InlineNotice({ children, tone = "info" }: PropsWithChildren<{ tone?: "info" | "warning" | "error" }>) {
  const color = tone === "error" ? tokens.color.danger : tone === "warning" ? tokens.color.warning : tokens.color.interactivePrimary;
  return (
    <View style={[styles.notice, { borderLeftColor: color }]}>
      <Text style={styles.noticeText}>{children}</Text>
    </View>
  );
}

export function ProgressBar({ value, color = tokens.color.program }: { value: number; color?: string }) {
  const normalized = Math.max(0, Math.min(value, 100));
  return (
    <View style={styles.progressTrack} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: normalized }}>
      <View style={[styles.progressFill, { backgroundColor: color, width: `${normalized}%` }]} />
    </View>
  );
}

export function LoadingState({ label = "Preparando tu día…" }: { label?: string }) {
  return (
    <Screen scroll={false} contentStyle={styles.loadingState}>
      <Brand />
      <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
      <Text style={styles.mutedText}>{label}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  notice: { backgroundColor: tokens.color.surfaceMuted, borderLeftWidth: 3, borderRadius: tokens.radius.md, padding: tokens.spacing.md },
  noticeText: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 8, overflow: "hidden" },
  progressFill: { borderRadius: tokens.radius.pill, height: "100%" },
  loadingState: { alignItems: "center", justifyContent: "center" },
  mutedText: { color: tokens.color.textMuted, fontSize: 15 },
});
