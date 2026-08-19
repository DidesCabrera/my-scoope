import { Paperclip } from "lucide-react-native";
import type { PropsWithChildren, ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Button, Card, SectionHeading } from "@/components/ui";
import type { EntityKind } from "@/components/ui";
import { NutritionKpiSection, type NutritionKpiSectionProps } from "@/components/nutrition";
import { tokens } from "@/design/tokens";
import {
  ProposalHeading,
  ProposalStatusBadge,
  type ProposalStatus,
  proposalTextStyles,
} from "./proposal-card";

export function ProposalDetailPage({
  children, isRead, objectives, proposedEntity, receivedAt, status, summary, title, typeLabel,
}: PropsWithChildren<{
  isRead: boolean; objectives?: ReactNode; proposedEntity?: ReactNode;
  receivedAt: string; status: ProposalStatus; summary?: string;
  title: string; typeLabel?: string;
}>) {
  return (
    <View style={styles.pageCard}>
      <View style={styles.hero}>
        <ProposalHeading detail isRead={isRead} receivedAt={receivedAt} title={title} />
        <View style={styles.badges}>
          <ProposalStatusBadge status={status} />
          {typeLabel ? <View style={styles.type}><Text style={styles.typeText}>{typeLabel}</Text></View> : null}
        </View>
        {summary || objectives ? (
          <View style={styles.requestSection}>
            <SectionHeading title="Detalles de la propuesta" />
            {summary ? <ProposalRequestSummary objectives={objectives} requirement={summary} /> : objectives}
          </View>
        ) : null}
      </View>
      {proposedEntity}
      {children}
    </View>
  );
}

export function ProposalRequestSummary({ objectives, requirement }: { objectives?: ReactNode; requirement: string }) {
  return (
    <View style={styles.requestSummary}>
      <View style={styles.requestCopy}>
        <Text style={proposalTextStyles.eyebrow}>Requerimiento</Text>
        <Text style={styles.requestText}>{requirement}</Text>
      </View>
      {objectives}
    </View>
  );
}

type ProposedEntityKind = Extract<EntityKind, "food" | "meal" | "dailyPlan" | "dpm" | "program">;

const proposedEntityLabels: Record<ProposedEntityKind, [singular: string, plural: string]> = {
  food: ["Alimento propuesto", "Alimentos propuestos"],
  meal: ["Comida propuesta", "Comidas propuestas"],
  dailyPlan: ["Plan propuesto", "Planes propuestos"],
  dpm: ["Plan de comidas propuesto", "Planes de comidas propuestos"],
  program: ["Programa propuesto", "Programas propuestos"],
};

export function ProposalEntitySection({ children, count = 1, detail, entity, title }: PropsWithChildren<{ count?: number; detail?: string; entity: ProposedEntityKind; title?: string }>) {
  const resolvedTitle = title ?? proposedEntityLabels[entity][count === 1 ? 0 : 1];
  return (
    <View style={styles.attachmentSection}>
      <SectionHeading detail={detail} icon={<Paperclip color={tokens.color.entityIconForeground} size={18} />} title={resolvedTitle} />
      {children}
    </View>
  );
}

export function ProposalObjectiveKpiSection(props: Omit<NutritionKpiSectionProps, "density" | "style">) {
  return <NutritionKpiSection {...props} />;
}

export function ProposalObjectiveSection({
  title = "Targets usados para validar la propuesta",
  ...nutrition
}: Omit<NutritionKpiSectionProps, "density" | "style"> & { title?: string }) {
  return (
    <View style={styles.objectiveSection}>
      <View style={styles.sectionHeader}>
        <Text style={proposalTextStyles.eyebrow}>Objetivos</Text>
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      <ProposalObjectiveKpiSection {...nutrition} />
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
  pageCard: { alignSelf: "stretch", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderTopColor: tokens.color.proposal, borderTopWidth: 3, borderWidth: 1, gap: tokens.spacing.lg, marginHorizontal: -tokens.spacing.screen, minWidth: 0, padding: tokens.card.outerPadding },
  hero: { gap: tokens.card.gap, minWidth: 0 },
  requestSection: { gap: tokens.spacing.sm, minWidth: 0 },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  type: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 6 },
  typeText: { color: tokens.color.textMain, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, textTransform: "uppercase" },
  requestSummary: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.md, padding: tokens.card.outerPadding },
  requestCopy: { gap: tokens.spacing.xs },
  requestText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, lineHeight: 20 },
  attachmentSection: { gap: tokens.spacing.sm, minWidth: 0 },
  sectionHeader: { gap: 3 },
  objectiveSection: { gap: tokens.spacing.sm, minWidth: 0 },
  sectionTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, lineHeight: 22 },
  metrics: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  metric: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, flexBasis: "47%", flexGrow: 1, gap: tokens.spacing.xs, minWidth: 120, padding: tokens.spacing.md },
  metricLabel: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.medium },
  metricValue: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold, fontVariant: ["tabular-nums"] },
  actions: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.spacing.sm, padding: tokens.card.outerPadding },
  actionsCopy: { gap: tokens.spacing.xs },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
});
