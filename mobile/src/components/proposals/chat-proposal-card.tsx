import { ChevronRight, GitCompareArrows } from "lucide-react-native";
import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";
import { ProposalCard, type ProposalAttachmentData } from "./proposal-card";

export function ChatProposalCard({
  adjustments = [],
  attachment = { kind: "dailyPlan", name: "DailyPlan propuesto" },
  current = true,
  metrics = [],
  onPress,
  receivedAt = "Generada ahora",
  summary,
  title,
}: {
  adjustments?: string[];
  attachment?: ProposalAttachmentData;
  current?: boolean;
  metrics?: { label: string; value: string }[];
  onPress(): void;
  receivedAt?: string;
  summary?: string;
  title: string;
}) {
  return (
    <ProposalCard
      action={<View style={styles.cta}><Text style={styles.ctaText}>{current ? "Revisar, aprobar y aplicar" : "Ver detalle"}</Text><ChevronRight color={tokens.color.interactivePrimary} size={17} /></View>}
      attachment={attachment}
      isRead
      onPress={onPress}
      receivedAt={receivedAt}
      status="pending"
      statusLabel={current ? "Lista para revisión" : "Propuesta anterior"}
      summary={summary}
      title={title}>
      {adjustments.length ? <View style={styles.iteration}>
        <View style={styles.iterationHeading}><GitCompareArrows color={tokens.color.textMuted} size={15} /><Text style={styles.iterationLabel}>Ajustes aplicados</Text></View>
        <View style={styles.adjustments}>{adjustments.map((item) => <View key={item} style={styles.adjustment}><Text style={styles.adjustmentText}>{item}</Text></View>)}</View>
      </View> : null}
      {metrics.length ? <View style={styles.metrics}>{metrics.map((metric) => <View key={metric.label} style={styles.metric}><Text style={styles.metricLabel}>{metric.label}</Text><Text style={styles.metricValue}>{metric.value}</Text></View>)}</View> : null}
    </ProposalCard>
  );
}

const styles = StyleSheet.create({
  iteration: { gap: tokens.spacing.sm },
  iterationHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  iterationLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  adjustments: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  adjustment: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  adjustmentText: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  metrics: { flexDirection: "row", gap: tokens.spacing.sm },
  metric: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, flex: 1, gap: tokens.spacing.xs, minWidth: 0, padding: tokens.spacing.sm },
  metricLabel: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.medium, textTransform: "uppercase" },
  metricValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  cta: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.xs },
  ctaText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.label, fontWeight: tokens.weight.bold },
});
