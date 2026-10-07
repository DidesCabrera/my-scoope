import { type Href, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import type { AIChatMessage, LibraryItem, ProposalDetail, ProposalSummary, SavedComparisonDetail, SavedComparisonSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { SavedComparisonListCard } from "@/components/comparisons";
import { LibraryCard } from "@/components/libraries/library-card";
import { ProposalListCard } from "@/components/proposals";
import { Button, Card, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

import { AssistantMessageText } from "./assistant-message-text";

type PreparedActionHandler = (actionId: string, mode: "commit" | "cancel", destructive: boolean) => void;
type ChatProposalCardData = Extract<NonNullable<AIChatMessage["cards"]>[number], { type: "proposal_review" | "generated_plan" }>;
type ChatLibraryCardData = Extract<NonNullable<AIChatMessage["cards"]>[number], { type: "library_item" }>;
type ChatComparisonCardData = Extract<NonNullable<AIChatMessage["cards"]>[number], { type: "saved_comparison" }>;

const librarySegments = { dailyplans: "daily-plans", foods: "foods", meals: "meals", programs: "programs" } as const;

function receivedTime(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString("es-CL", { hour: "2-digit", hour12: false, minute: "2-digit" });
}

function ChatProposalListCard({ card }: { card: ChatProposalCardData }) {
  const router = useRouter();
  const { apiRequest } = useSession();
  const [loadedProposal, setLoadedProposal] = useState<ProposalSummary | null>(null);
  const [failedProposalId, setFailedProposalId] = useState<number | null>(null);
  const proposalId = card.proposal_id;
  const proposal = card.proposal ?? (loadedProposal?.id === proposalId ? loadedProposal : null);
  const failed = proposalId == null || failedProposalId === proposalId;

  useEffect(() => {
    if (card.proposal || !proposalId) return undefined;
    let active = true;
    void apiRequest<ProposalDetail>(`/api/v1/proposals/${proposalId}`)
      .then((nextProposal) => { if (active) setLoadedProposal(nextProposal); })
      .catch(() => { if (active) setFailedProposalId(proposalId); });
    return () => { active = false; };
  }, [apiRequest, card.proposal, proposalId]);

  if (proposal) {
    return <ProposalListCard onPress={() => router.push(`/proposals/${proposal.id}` as Href)} proposal={proposal} />;
  }
  if (!failed) {
    return <View accessibilityLabel="Cargando propuesta" style={styles.proposalLoading}><ActivityIndicator color={tokens.color.textMuted} /></View>;
  }
  return <Card accent={tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text>{card.summary ? <Text style={styles.cardCopy}>{card.summary}</Text> : null}{proposalId ? <Button label="Abrir propuesta" onPress={() => router.push(`/proposals/${proposalId}` as Href)} /> : null}</Card>;
}

function ChatLibraryCard({ card }: { card: ChatLibraryCardData }) {
  const { apiRequest } = useSession();
  const [item, setItem] = useState<LibraryItem | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void apiRequest<LibraryItem>(`/api/v1/library/${librarySegments[card.resource]}/${card.item_id}`)
      .then((nextItem) => { if (active) setItem(nextItem); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [apiRequest, card.item_id, card.resource]);

  if (item) return <LibraryCard apiRequest={apiRequest} interactive={false} item={item} onChanged={() => undefined} />;
  if (!failed) return <View accessibilityLabel={`Cargando ${card.title}`} style={styles.cardLoading}><ActivityIndicator color={tokens.color.textMuted} /></View>;
  return <InlineNotice>Este elemento de la biblioteca ya no está disponible.</InlineNotice>;
}

function ChatSavedComparisonCard({ card }: { card: ChatComparisonCardData }) {
  const router = useRouter();
  const { apiRequest } = useSession();
  const [item, setItem] = useState<SavedComparisonSummary | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void apiRequest<SavedComparisonDetail>(`/api/v1/comparisons/saved/${card.comparison_id}`)
      .then((detail) => {
        if (!active) return;
        setItem({
          id: detail.saved_comparison_id ?? card.comparison_id,
          item_count: detail.items.length,
          items: detail.items,
          kind: detail.kind,
          kind_label: detail.kind_label,
          name: detail.saved_comparison_name || card.title,
          updated_at: detail.updated_at,
        });
      })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [apiRequest, card.comparison_id, card.title]);

  if (item) return <SavedComparisonListCard item={item} onPress={() => router.push(`/comparator/saved/${item.id}` as Href)} />;
  if (!failed) return <View accessibilityLabel={`Cargando ${card.title}`} style={styles.cardLoading}><ActivityIndicator color={tokens.color.textMuted} /></View>;
  return <InlineNotice>Esta comparación ya no está disponible.</InlineNotice>;
}

function ChatCard({ card, onPreferenceCommit, onPreparedAction }: { card: NonNullable<AIChatMessage["cards"]>[number]; onPreferenceCommit: () => void; onPreparedAction: PreparedActionHandler }) {
  if (card.type === "proposal_review" || card.type === "generated_plan") {
    return <ChatProposalListCard card={card} />;
  }
  if (card.type === "library_item") {
    return <ChatLibraryCard card={card} />;
  }
  if (card.type === "saved_comparison") {
    return <ChatSavedComparisonCard card={card} />;
  }
  if (card.type === "prepared_action") {
    const pending = card.status === "prepared";
    return <Card accent={card.destructive ? tokens.color.danger : tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text><Text style={styles.cardMeta}>{card.operation_count} {card.operation_count === 1 ? "cambio" : "cambios"} · riesgo {card.risk_level}</Text>{card.summary ? <Text style={styles.cardCopy}>{card.summary}</Text> : null}{card.operations.map((operation, index) => <Text key={`${index}-${operation}`} style={styles.operation}>• {operation}</Text>)}{pending ? <View style={styles.actions}><Button label="Confirmar" onPress={() => onPreparedAction(card.action_id, "commit", card.destructive)} variant={card.destructive ? "danger" : "primary"} /><Button label="Cancelar" onPress={() => onPreparedAction(card.action_id, "cancel", false)} variant="secondary" /></View> : <InlineNotice>Acción {card.status === "committed" ? "confirmada" : card.status === "cancelled" ? "cancelada" : "no disponible"}.</InlineNotice>}</Card>;
  }
  return <Card accent={tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text>{card.subtitle ? <Text style={styles.cardCopy}>{card.subtitle}</Text> : null}{card.items.map((item) => <View key={`${card.type}-${item.key}`} style={styles.item}><Text style={styles.itemLabel}>{item.label}</Text><Text style={[styles.itemValue, item.is_pending && styles.pending]}>{item.value}</Text></View>)}{card.type === "preference_draft" && card.can_commit ? <Button label="Guardar preferencias" onPress={onPreferenceCommit} /> : null}</Card>;
}

export function ChatConversation({ messages, onPreferenceCommit, onPreparedAction }: { messages: AIChatMessage[]; onPreferenceCommit: () => void; onPreparedAction: PreparedActionHandler }) {
  return (
    <View accessibilityLabel="Conversación con el Asistente" style={styles.conversation}>
      {messages.map((message, index) => {
        const isUser = message.role === "user";
        const time = !isUser && index === messages.length - 1 ? receivedTime(message.created_at) : null;
        return (
          <View key={message.id} style={[styles.message, isUser ? styles.userMessage : styles.assistantMessage]}>
            <View style={isUser ? styles.userBubble : styles.assistantContent}>
              {message.text ? (isUser ? <Text style={styles.text}>{message.text}</Text> : <AssistantMessageText>{message.text}</AssistantMessageText>) : null}
              {message.cards?.map((card, index) => <ChatCard card={card} key={`${message.id}-${card.type}-${index}`} onPreferenceCommit={onPreferenceCommit} onPreparedAction={onPreparedAction} />)}
              {message.has_structured_content && !message.cards?.length ? <InlineNotice>Este objeto no está disponible en esta versión de la app.</InlineNotice> : null}
            </View>
            {time ? <Text accessibilityLabel={`Recibido a las ${time}`} style={styles.receivedTime}>{time}</Text> : null}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  assistantContent: { gap: tokens.spacing.md, width: "100%" },
  assistantMessage: { alignItems: "stretch" },
  actions: { gap: tokens.spacing.sm },
  conversation: { gap: tokens.spacing.xxl },
  cardCopy: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  cardMeta: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: "700" },
  cardTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "800" },
  cardLoading: { alignItems: "center", minHeight: 120, justifyContent: "center" },
  item: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: 2, paddingTop: tokens.spacing.sm },
  itemLabel: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: "700" },
  itemValue: { color: tokens.color.textMain, fontSize: tokens.type.body },
  message: { width: "100%" },
  pending: { color: tokens.color.textMuted },
  proposalLoading: { alignItems: "center", minHeight: 120, justifyContent: "center" },
  receivedTime: { color: tokens.color.textSubtle, fontSize: tokens.type.label, marginTop: tokens.spacing.sm },
  operation: { color: tokens.color.textMain, fontSize: tokens.type.caption },
  text: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 25 },
  userBubble: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.card, gap: tokens.spacing.sm, maxWidth: "86%", paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.md },
  userMessage: { alignItems: "flex-end" },
});
