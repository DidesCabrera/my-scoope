import { Route } from "lucide-react-native";
import type { PropsWithChildren } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Button, Card } from "@/components/ui";
import { tokens } from "@/design/tokens";
import {
  ProposalAttachment,
  type ProposalAttachmentData,
  ProposalHeading,
  ProposalStatusBadge,
  type ProposalStatus,
  ProposalSummary,
  proposalTextStyles,
} from "./proposal-card";

export function ProposalDetailPage({
  attachment, children, intent, isRead, receivedAt, status, summary, title, typeLabel,
}: PropsWithChildren<{
  attachment?: ProposalAttachmentData; intent?: string; isRead: boolean;
  receivedAt: string; status: ProposalStatus; summary?: string;
  title: string; typeLabel?: string;
}>) {
  return (
    <View style={styles.page}>
      <Card accent={tokens.color.proposal}>
        <ProposalHeading detail isRead={isRead} receivedAt={receivedAt} title={title} />
        <View style={styles.badges}>
          <ProposalStatusBadge status={status} />
          {typeLabel ? <View style={styles.type}><Text style={styles.typeText}>{typeLabel}</Text></View> : null}
        </View>
        {summary ? <ProposalSummary>{summary}</ProposalSummary> : null}
      </Card>
      {intent ? <View style={styles.context}><Route color={tokens.color.textMuted} size={16} /><Text style={styles.contextText}>Intent: <Text style={styles.contextStrong}>{intent}</Text></Text></View> : null}
      {attachment ? <ProposalReviewSection eyebrow="Adjunto" title="Entidad propuesta"><ProposalAttachment attachment={attachment} /></ProposalReviewSection> : null}
      {children}
    </View>
  );
}

export function ProposalReviewSection({ children, eyebrow, title }: PropsWithChildren<{ eyebrow?: string; title: string }>) {
  return (
    <Card>
      <View style={styles.sectionHeader}>
        {eyebrow ? <Text style={proposalTextStyles.eyebrow}>{eyebrow}</Text> : null}
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      {children}
    </Card>
  );
}

export function ProposalMetricGrid({ metrics }: { metrics: { label: string; value: string }[] }) {
  return <View style={styles.metrics}>{metrics.map((metric) => <View key={metric.label} style={styles.metric}><Text style={styles.metricLabel}>{metric.label}</Text><Text style={styles.metricValue}>{metric.value}</Text></View>)}</View>;
}

export function ProposalReviewActions({ description, onApprove, onCancel, onReject }: { description: string; onApprove?: () => void; onCancel?: () => void; onReject?: () => void }) {
  return (
    <View style={styles.actions}>
      <View style={styles.actionsCopy}><Text style={proposalTextStyles.eyebrow}>Revisión humana</Text><Text style={styles.description}>{description}</Text></View>
      {onApprove ? <Button label="Aprobar propuesta" onPress={onApprove} /> : null}
      {onReject ? <Button label="Rechazar propuesta" onPress={onReject} variant="danger" /> : null}
      {onCancel ? <Button label="Cancelar propuesta" onPress={onCancel} variant="secondary" /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  type: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 6 },
  typeText: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, textTransform: "uppercase" },
  context: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  contextText: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  contextStrong: { color: tokens.color.textMain, fontWeight: tokens.weight.bold },
  sectionHeader: { gap: 3 },
  sectionTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 22 },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  metric: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexBasis: "47%", flexGrow: 1, gap: tokens.spacing.xs, minWidth: 120, padding: tokens.spacing.md },
  metricLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  metricValue: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  actions: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.card.outerPadding },
  actionsCopy: { gap: tokens.spacing.xs },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
});
