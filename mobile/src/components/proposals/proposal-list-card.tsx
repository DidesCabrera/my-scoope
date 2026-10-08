import { ChevronRight } from "lucide-react-native";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ProposalStatus as ApiProposalStatus, ProposalSummary } from "@/api/types";
import { EntityCardAction, EntityCardActions, SectionIcon } from "@/components/ui";
import { Card, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { formatCompactDate } from "@/presentation/date";

import { ProposalStatusBadge, ProposalTypeBadge, type ProposalStatus } from "./proposal-card";

const proposalEntityColors: Record<ProposalSummary["attachment_kind"], string> = {
  brief: tokens.color.proposal,
  dailyplan: tokens.color.dailyPlan,
  meal: tokens.color.meal,
  program: tokens.color.program,
};

function proposalCardStatus(status: ApiProposalStatus): ProposalStatus {
  if (status === "pending_review" || status === "draft") return "pending";
  return status;
}

export function ProposalListCard({ proposal, onPress }: { proposal: ProposalSummary; onPress(): void }) {
  const detailLabel = `Ver detalle de ${proposal.title}`;
  return (
      <Card accent={proposalEntityColors[proposal.attachment_kind]} style={styles.proposalCard}>
        <Pressable accessibilityLabel={detailLabel} accessibilityRole="link" onPress={onPress} style={({ pressed }) => [styles.cardLink, pressed && styles.pressed]}>
        <View style={styles.copy}>
          <View style={styles.eyebrowRow}>
            <SectionIcon section="proposal" size="compact" />
            <Text style={styles.eyebrow}>Propuesta</Text>
          </View>
          <Text style={styles.title}>{proposal.title}</Text>
          <Text style={textStyles.caption}>{formatCompactDate(proposal.created_at) ?? "Sin fecha"}</Text>
          <View style={styles.proposalBadges}>
            <ProposalStatusBadge status={proposalCardStatus(proposal.status)} />
            <ProposalTypeBadge kind={proposal.attachment_kind} />
          </View>
        </View>
        {proposal.summary ? <Text numberOfLines={3} style={textStyles.muted}>{proposal.summary}</Text> : null}
        <View style={styles.attachment}>
          <View style={styles.copy}>
            <Text style={textStyles.caption}>{proposal.attachment_label}</Text>
            <Text style={textStyles.strong}>{proposal.attachment_name}</Text>
          </View>
        </View>
        </Pressable>
        <EntityCardActions>
          <EntityCardAction label={detailLabel} onPress={onPress} role="link">
            <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
          </EntityCardAction>
        </EntityCardActions>
      </Card>
  );
}

const styles = StyleSheet.create({
  attachment: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.lg, padding: tokens.spacing.md },
  cardLink: { gap: tokens.card.gap },
  copy: { flex: 1, gap: 4 },
  eyebrow: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, textTransform: "uppercase" },
  eyebrowRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.compact },
  pressed: { opacity: 0.65 },
  proposalCard: { paddingBottom: tokens.card.innerPadding },
  proposalBadges: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm, paddingTop: tokens.spacing.xs },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
