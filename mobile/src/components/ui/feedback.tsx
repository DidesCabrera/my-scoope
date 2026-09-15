import type { PropsWithChildren } from "react";
import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react-native";
import { ActivityIndicator, Modal, StyleSheet, Text, View } from "react-native";

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
    <Screen scroll={false} contentStyle={styles.loadingState} headerMode="preserve">
      <Brand />
      <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
      <Text style={styles.mutedText}>{label}</Text>
    </Screen>
  );
}

export type MutationStatus = {
  loadingLabel: string;
  phase: "loading" | "success";
  successLabel: string;
};

export function MutationStatusModal({ onFinished, status }: { onFinished(): void; status: MutationStatus | null }) {
  useEffect(() => {
    if (status?.phase !== "success") return;
    const timer = setTimeout(onFinished, 900);
    return () => clearTimeout(timer);
  }, [onFinished, status?.phase]);

  if (!status) return null;
  const loading = status.phase === "loading";
  return (
    <Modal
      animationType="fade"
      navigationBarTranslucent
      onRequestClose={() => undefined}
      presentationStyle="overFullScreen"
      statusBarTranslucent
      transparent
      visible>
      <View accessibilityLiveRegion="polite" accessibilityRole="alert" style={styles.statusScrim}>
        <View style={styles.statusCard}>
          {loading
            ? <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
            : <CheckCircle2 color={tokens.color.success} size={36} strokeWidth={2.2} />}
          <Text style={styles.statusLabel}>{loading ? status.loadingLabel : status.successLabel}</Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  notice: { backgroundColor: tokens.color.surfaceMuted, borderLeftWidth: 3, borderRadius: tokens.radius.md, padding: tokens.spacing.md },
  noticeText: { color: tokens.color.textMuted, fontSize: 14, lineHeight: 20 },
  progressTrack: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 8, overflow: "hidden" },
  progressFill: { borderRadius: tokens.radius.pill, height: "100%" },
  loadingState: { alignItems: "center", justifyContent: "center" },
  mutedText: { color: tokens.color.textMuted, fontSize: 15 },
  statusCard: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, minWidth: 240, paddingHorizontal: tokens.spacing.xl, paddingVertical: tokens.spacing.xl },
  statusLabel: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.semibold, textAlign: "center" },
  statusScrim: { alignItems: "center", backgroundColor: "rgba(0, 0, 0, 0.56)", flex: 1, justifyContent: "center", padding: tokens.spacing.screen },
});
