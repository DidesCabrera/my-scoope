import { ChevronRight, ClipboardCheck, GitCompareArrows } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { tokens } from "@/design/tokens";

export function ChatProposalCard({ adjustments = [], current = true, metrics = [], onPress, summary, title }: {
  adjustments?: string[]; current?: boolean; metrics?: { label: string; value: string }[];
  onPress(): void; summary?: string; title: string;
}) {
  return (
    <Pressable accessibilityLabel={`Revisar propuesta: ${title}`} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.card, current && styles.current, pressed && styles.pressed]}>
      <View style={styles.header}>
        <View style={styles.headerCopy}><Text style={styles.eyebrow}>{current ? "Lista para revisión" : "Propuesta anterior"}</Text><Text style={styles.title}>{title}</Text></View>
        <View style={styles.icon}><ClipboardCheck color={tokens.color.entityIconForeground} size={16} /></View>
      </View>
      {summary ? <Text style={styles.summary}>{summary}</Text> : null}
      {adjustments.length ? <View style={styles.iteration}>
        <View style={styles.iterationHeading}><GitCompareArrows color={tokens.color.textMuted} size={15} /><Text style={styles.iterationLabel}>Ajustes aplicados</Text></View>
        <View style={styles.adjustments}>{adjustments.map((item) => <View key={item} style={styles.adjustment}><Text style={styles.adjustmentText}>{item}</Text></View>)}</View>
      </View> : null}
      {metrics.length ? <View style={styles.metrics}>{metrics.map((metric) => <View key={metric.label} style={styles.metric}><Text style={styles.metricLabel}>{metric.label}</Text><Text style={styles.metricValue}>{metric.value}</Text></View>)}</View> : null}
      <View style={styles.cta}><Text style={styles.ctaText}>{current ? "Revisar, aprobar y aplicar" : "Ver detalle de la propuesta"}</Text><ChevronRight color={tokens.color.interactivePrimary} size={17} /></View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.md, padding: tokens.card.innerPadding },
  current: { borderColor: tokens.color.proposal, borderWidth: 2 }, pressed: { opacity: 0.72 },
  header: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  headerCopy: { flex: 1, gap: tokens.spacing.xs, minWidth: 0 },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0.7, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 22 },
  icon: { alignItems: "center", backgroundColor: tokens.color.proposal, borderRadius: tokens.radius.sm, height: 28, justifyContent: "center", width: 28 },
  summary: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  iteration: { gap: tokens.spacing.sm }, iterationHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  iterationLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  adjustments: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.xs },
  adjustment: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.xs },
  adjustmentText: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  metrics: { flexDirection: "row", gap: tokens.spacing.sm },
  metric: { backgroundColor: tokens.color.surfaceCard, borderRadius: tokens.radius.lg, flex: 1, gap: tokens.spacing.xs, minWidth: 0, padding: tokens.spacing.sm },
  metricLabel: { color: tokens.color.textMuted, fontSize: 10, fontWeight: tokens.weight.medium, textTransform: "uppercase" },
  metricValue: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  cta: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingTop: tokens.spacing.sm },
  ctaText: { color: tokens.color.interactivePrimary, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
});
