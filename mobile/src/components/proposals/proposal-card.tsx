import { Mail, MailOpen, Paperclip } from "lucide-react-native";
import type { PropsWithChildren, ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card, EntityIcon, SectionIcon, type EntityKind } from "@/components/ui";
import { tokens } from "@/design/tokens";

export type ProposalStatus = "pending" | "approved" | "applied" | "rejected" | "cancelled";
export type ProposalAttachmentData = {
  kind: Extract<EntityKind, "dailyPlan" | "dpm" | "food" | "meal">;
  name: string;
};

const labels: Record<ProposalStatus, string> = {
  pending: "Pendiente", approved: "Aprobada", applied: "Aplicada",
  rejected: "Rechazada", cancelled: "Cancelada",
};

function statusColor(status: ProposalStatus): string {
  if (status === "approved") return tokens.color.success;
  if (status === "applied") return tokens.color.interactivePrimary;
  if (status === "rejected" || status === "cancelled") return tokens.color.danger;
  return tokens.color.warning;
}

export function ProposalStatusBadge({ status, label }: { status: ProposalStatus; label?: string }) {
  const color = statusColor(status);
  return (
    <View style={[styles.status, { backgroundColor: `${color}1A`, borderColor: `${color}55` }]}>
      <Text style={[styles.statusText, { color }]}>{label ?? labels[status]}</Text>
    </View>
  );
}

export function ProposalAttachment({ attachment }: { attachment: ProposalAttachmentData }) {
  return (
    <View accessibilityLabel={`Adjunto: ${attachment.name}`} style={styles.attachment}>
      <EntityIcon entity={attachment.kind} size="compact" />
      <Text numberOfLines={1} style={styles.attachmentName}>{attachment.name}</Text>
    </View>
  );
}

export function ProposalCard({
  action, attachment, children, isRead, onPress, receivedAt, status, statusLabel, summary, title,
}: PropsWithChildren<{
  action?: ReactNode; attachment: ProposalAttachmentData; isRead: boolean;
  onPress?: () => void; receivedAt: string; status: ProposalStatus;
  statusLabel?: string; summary?: string; title: string;
}>) {
  const content = (
    <Card accent={tokens.color.proposal}>
      <ProposalHeading isRead={isRead} receivedAt={receivedAt} title={title} />
      <ProposalStatusBadge label={statusLabel} status={status} />
      {summary ? <ProposalSummary>{summary}</ProposalSummary> : null}
      {children}
      <View style={styles.footer}>
        <Paperclip color={tokens.color.textSoft} size={16} />
        <ProposalAttachment attachment={attachment} />
        {action}
      </View>
    </Card>
  );
  if (!onPress) return content;
  return <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>{content}</Pressable>;
}

export function ProposalHeading({ isRead, receivedAt, title, detail = false }: { isRead: boolean; receivedAt: string; title: string; detail?: boolean }) {
  return (
    <View style={styles.copy}>
      <View style={styles.entityEyebrow}>
        <SectionIcon section="proposal" size="compact" />
        <Text style={styles.headingEyebrow}>Propuesta</Text>
      </View>
      <Text style={[styles.title, detail && styles.detailTitle]}>{title}</Text>
      <View style={styles.received}>
        {isRead ? <MailOpen color={tokens.color.textMuted} size={14} /> : <Mail color={tokens.color.textMuted} size={14} />}
        <Text style={styles.receivedText}>{receivedAt}</Text>
      </View>
    </View>
  );
}

export function ProposalSummary({ children }: { children: string }) {
  return <View style={styles.summary}><Text style={proposalTextStyles.eyebrow}>Requerimiento</Text><Text style={styles.summaryText}>{children}</Text></View>;
}

export const proposalTextStyles = StyleSheet.create({
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0.7, textTransform: "uppercase" },
});

const styles = StyleSheet.create({
  pressed: { opacity: 0.72 },
  copy: { gap: tokens.spacing.compact, minWidth: 0 },
  entityEyebrow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  headingEyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0, textTransform: "uppercase" },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.bold, lineHeight: 24 },
  detailTitle: { fontSize: tokens.type.title, lineHeight: 30 },
  received: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  receivedText: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.weight.regular },
  status: { alignSelf: "flex-start", borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 6 },
  statusText: { fontSize: tokens.type.label, fontWeight: tokens.weight.bold, textTransform: "uppercase" },
  summary: { backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.lg, borderWidth: 1, gap: tokens.spacing.xs, padding: tokens.spacing.md },
  summaryText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, lineHeight: 20 },
  footer: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  attachment: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, maxWidth: "100%", paddingHorizontal: tokens.spacing.sm, paddingVertical: tokens.spacing.compact },
  attachmentName: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
});
