import { type Href, useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import type { AIChatMessage } from "@/api/types";
import { Button, Card, InlineNotice } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type PreparedActionHandler = (actionId: string, mode: "commit" | "cancel", destructive: boolean) => void;

function ChatCard({ card, onPreparedAction }: { card: NonNullable<AIChatMessage["cards"]>[number]; onPreparedAction: PreparedActionHandler }) {
  const router = useRouter();
  if (card.type === "proposal_review" || card.type === "generated_plan") {
    const proposalId = card.proposal_id;
    return <Card accent={tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text>{card.summary ? <Text style={styles.cardCopy}>{card.summary}</Text> : null}{proposalId ? <Button label="Abrir propuesta" onPress={() => router.push(`/proposals/${proposalId}` as Href)} /> : null}</Card>;
  }
  if (card.type === "saved_comparison") {
    return <Card accent={tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text><Button label="Abrir comparación" onPress={() => router.push(`/comparator/saved/${card.comparison_id}` as Href)} /></Card>;
  }
  if (card.type === "prepared_action") {
    const pending = card.status === "prepared";
    return <Card accent={card.destructive ? tokens.color.danger : tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text>{card.summary ? <Text style={styles.cardCopy}>{card.summary}</Text> : null}{pending ? <View style={styles.actions}><Button label="Confirmar" onPress={() => onPreparedAction(card.action_id, "commit", card.destructive)} variant={card.destructive ? "danger" : "primary"} /><Button label="Cancelar" onPress={() => onPreparedAction(card.action_id, "cancel", false)} variant="secondary" /></View> : <InlineNotice>Acción {card.status === "committed" ? "confirmada" : card.status === "cancelled" ? "cancelada" : "no disponible"}.</InlineNotice>}</Card>;
  }
  return <Card accent={tokens.color.interactivePrimary}><Text style={styles.cardTitle}>{card.title}</Text>{card.subtitle ? <Text style={styles.cardCopy}>{card.subtitle}</Text> : null}{card.items.map((item) => <View key={`${card.type}-${item.key}`} style={styles.item}><Text style={styles.itemLabel}>{item.label}</Text><Text style={[styles.itemValue, item.is_pending && styles.pending]}>{item.value}</Text></View>)}</Card>;
}

export function ChatConversation({ messages, onPreparedAction }: { messages: AIChatMessage[]; onPreparedAction: PreparedActionHandler }) {
  return (
    <View accessibilityLabel="Conversación con el Asistente" style={styles.conversation}>
      {messages.map((message) => {
        const isUser = message.role === "user";
        return (
          <View key={message.id} style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
            <Text style={styles.role}>{isUser ? "Tú" : "Asistente"}</Text>
            {message.text ? <Text style={styles.text}>{message.text}</Text> : null}
            {message.cards?.map((card, index) => <ChatCard card={card} key={`${message.id}-${card.type}-${index}`} onPreparedAction={onPreparedAction} />)}
            {message.has_structured_content && !message.cards?.length ? <InlineNotice>Este objeto no está disponible en esta versión de la app.</InlineNotice> : null}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  assistantBubble: { alignSelf: "flex-start", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderWidth: 1 },
  actions: { gap: tokens.spacing.sm },
  bubble: { borderRadius: tokens.radius.card, gap: tokens.spacing.sm, maxWidth: "92%", padding: tokens.spacing.md },
  conversation: { gap: tokens.spacing.md },
  cardCopy: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  cardTitle: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: "800" },
  item: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: 2, paddingTop: tokens.spacing.sm },
  itemLabel: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: "700" },
  itemValue: { color: tokens.color.textMain, fontSize: tokens.type.body },
  pending: { color: tokens.color.textMuted },
  role: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "900", textTransform: "uppercase" },
  text: { color: tokens.color.textMain, fontSize: tokens.type.body, lineHeight: 24 },
  userBubble: { alignSelf: "flex-end", backgroundColor: tokens.color.surfaceMuted, borderColor: tokens.color.interactivePrimary, borderWidth: 1 },
});
