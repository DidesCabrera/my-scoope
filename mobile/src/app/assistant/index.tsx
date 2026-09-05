import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { AIChatListData, AIChatSummary } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { SectionPageHeader } from "@/components/ui";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, InlineNotice, LoadingState, Pill, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function ChatCard({ chat, onPress }: { chat: AIChatSummary; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
      <Card>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.title}>{chat.title}</Text>
            <Text style={textStyles.caption}>{new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(chat.updated_at))}</Text>
          </View>
          <Pill label={chat.status_label} />
        </View>
        <Text numberOfLines={3} style={textStyles.muted}>{chat.last_message_preview}</Text>
        <Text style={textStyles.caption}>{chat.message_count} mensajes · Continuar ›</Text>
      </Card>
    </Pressable>
  );
}

export default function AssistantHistoryScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<AIChatListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try { setPage(await apiRequest<AIChatListData>("/api/v1/ai/chats?limit=50")); }
    catch (nextError) { setError(userFacingError(nextError)); }
    finally { setLoading(false); }
  }, [apiRequest]);
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { icon: "plus", label: "Nuevo chat", onPress: () => router.push("/assistant/new" as Href) },
      mode: "default",
      title: "Asistente",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [router, setHeaderPresentation]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Abriendo tus conversaciones…" />;
  return (
    <Screen headerMode="preserve">
      <SectionPageHeader count={page?.total} countLabel="conversaciones" section="chat" title="Asistente AI" />
      {page?.availability ? <InlineNotice>{page.availability.available_credits} créditos disponibles · {page.availability.label}</InlineNotice> : null}
      {page?.availability.available_credits === 0 ? <Card accent={tokens.color.warning}>
        <Text style={styles.creditTitle}>No tienes créditos disponibles</Text>
        <Text style={styles.creditCopy}>Agrega créditos para iniciar una conversación nueva o continuar una existente.</Text>
        <Button label="Comprar créditos" onPress={() => router.push("/subscription" as Href)} />
      </Card> : null}
      {page?.pending_new_turn ? <InlineNotice tone="warning">Hay una conversación nueva procesándose. Ábrela para recuperar su resultado.</InlineNotice> : null}
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {page?.items.length ? page.items.map((chat) => <ChatCard chat={chat} key={chat.id} onPress={() => router.push(`/assistant/${chat.id}` as Href)} />) : (
        <EmptyState actionLabel="Iniciar conversación" message="Conversa con el Asistente para definir o ajustar tu planificación nutricional." onAction={() => router.push("/assistant/new" as Href)} title="Aún no tienes chats" />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: tokens.spacing.xs },
  creditCopy: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  creditTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  pressed: { opacity: 0.7 },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  title: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
});
