import * as Crypto from "expo-crypto";
import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { Sparkles } from "lucide-react-native";

import { pollAsyncJob } from "@/api/async-job";
import { userFacingError } from "@/api/errors";
import type {
  AIChatDetail,
  AIChatListData,
  AIJobAcceptedData,
  AIPendingTurn,
  AITurnResultData,
  AssistantAvailability,
  AIPreparedActionResult,
} from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { Button, Card, InlineNotice, LoadingState, Screen } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

import { ChatComposer } from "./chat-composer";
import { ChatConversation } from "./chat-conversation";

export function AssistantChatScreen({ chatId, comparisonId = null }: { chatId: number | null; comparisonId?: number | null }) {
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [chat, setChat] = useState<AIChatDetail | null>(null);
  const [availability, setAvailability] = useState<AssistantAvailability | null>(null);
  const [pending, setPending] = useState<AIPendingTurn | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iterationWarning, setIterationWarning] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      if (chatId) {
        const next = await apiRequest<AIChatDetail>(`/api/v1/ai/chats/${chatId}`);
        setChat(next);
        setAvailability(next.availability);
        setPending(next.pending_turn);
      } else {
        const page = await apiRequest<AIChatListData>("/api/v1/ai/chats?limit=1");
        setAvailability(page.availability);
        setPending(page.pending_new_turn);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, chatId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      fallback: "/assistant",
      mode: "back",
      title: chat?.title ?? (chatId ? "Conversación" : "Nuevo chat"),
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [chat?.title, chatId, setHeaderPresentation]));

  useEffect(() => {
    if (!pending || status !== "authenticated") return;
    const controller = new AbortController();
    void pollAsyncJob<AITurnResultData>({
      path: `/api/v1/ai/jobs/${pending.job_id}`,
      request: (path) => apiRequest(path),
      signal: controller.signal,
    })
      .then((result) => {
        if (controller.signal.aborted) return;
        setPending(null);
        setIterationWarning(result.has_iteration_warning);
        if (!chatId || result.chat_id !== chatId) {
          router.replace(`/assistant/${result.chat_id}` as Href);
        } else {
          void load();
        }
      })
      .catch((nextError) => {
        if (nextError instanceof Error && nextError.name === "AbortError") return;
        setError(userFacingError(nextError));
      })
      .finally(() => { if (!controller.signal.aborted) setSending(false); });
    return () => controller.abort();
  }, [apiRequest, chatId, load, pending, router, status]);

  async function send() {
    const normalized = message.trim();
    if (!normalized || sending || pending) return;
    setSending(true);
    setError(null);
    try {
      const accepted = await apiRequest<AIJobAcceptedData>("/api/v1/ai/turns", {
        method: "POST",
        body: JSON.stringify({
          message: normalized,
          idempotency_key: `mobile-${Crypto.randomUUID()}`,
          chat_id: chatId,
          comparison_id: comparisonId,
        }),
      });
      setMessage("");
      setPending(accepted);
    } catch (nextError) {
      setError(userFacingError(nextError));
      setSending(false);
    }
  }

  function handlePreparedAction(actionId: string, mode: "commit" | "cancel", destructive: boolean) {
    const execute = async () => {
      setError(null);
      try {
        await apiRequest<AIPreparedActionResult>(`/api/v1/ai/prepared-actions/${actionId}/${mode}`, { method: "POST" });
        await load();
      } catch (nextError) {
        setError(userFacingError(nextError));
        await load();
      }
    };
    Alert.alert(
      mode === "commit" ? "¿Confirmar esta acción?" : "¿Cancelar esta acción?",
      mode === "commit" ? "El cambio se ejecutará ahora usando la acción que revisaste." : "La acción quedará cancelada y no realizará cambios.",
      [
        { text: "Volver", style: "cancel" },
        { text: mode === "commit" ? "Confirmar" : "Cancelar acción", style: destructive || mode === "cancel" ? "destructive" : "default", onPress: () => void execute() },
      ],
    );
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Preparando la conversación…" />;

  const unavailable = !availability?.is_available;
  const outOfCredits = availability?.available_credits === 0;
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
      <Screen contentStyle={styles.screen} headerMode="preserve" scroll={false}>
        <ScrollView
          contentContainerStyle={styles.chatContent}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: false })}
          ref={scrollRef}
          showsVerticalScrollIndicator={false}>
          {outOfCredits || unavailable || error || iterationWarning || comparisonId ? <View style={styles.notices}>
            {outOfCredits ? <Card accent={tokens.color.warning}>
              <Text style={styles.creditTitle}>No tienes créditos disponibles</Text>
              <Text style={styles.creditCopy}>Puedes abrir y revisar tus chats. Para enviar un mensaje nuevo, agrega créditos desde los planes disponibles.</Text>
              <Button label="Comprar créditos" onPress={() => router.push("/subscription" as Href)} />
            </Card> : unavailable ? <InlineNotice tone="warning">El Asistente no está disponible en este momento.</InlineNotice> : null}
            {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
            {iterationWarning ? <InlineNotice tone="warning">La conversación se guardó, pero una iteración del plan requiere revisión.</InlineNotice> : null}
            {comparisonId ? <InlineNotice>Esta conversación usará la comparación guardada como contexto verificado.</InlineNotice> : null}
          </View> : null}
          {chat?.messages.length ? <ChatConversation messages={chat.messages} onPreparedAction={handlePreparedAction} /> : (
            <View style={styles.emptyConversation}>
              <View style={styles.emptyIcon}><Sparkles color={tokens.color.textMain} size={24} strokeWidth={2} /></View>
              <Text style={styles.emptyTitle}>¿Qué quieres planificar?</Text>
              <Text style={styles.emptyCopy}>Cuéntame qué quieres crear o ajustar. Esta conversación se irá guardando automáticamente.</Text>
            </View>
          )}
          {pending || sending ? <View accessibilityLiveRegion="polite" style={styles.thinking}><ActivityIndicator color={tokens.color.textMuted} size="small" /><Text style={styles.thinkingText}>El Asistente está respondiendo…</Text></View> : null}
        </ScrollView>
        <ChatComposer
          disabled={unavailable || outOfCredits || Boolean(pending)}
          loading={sending}
          maxLength={availability?.max_message_chars ?? 2000}
          onChangeText={setMessage}
          onSend={() => void send()}
          supportingText={availability ? `${availability.available_credits} ${availability.available_credits === 1 ? "crédito disponible" : "créditos disponibles"}` : undefined}
          value={message}
        />
      </Screen>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  chatContent: { flexGrow: 1, gap: tokens.spacing.xl, paddingBottom: tokens.spacing.xxl, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  creditCopy: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 23 },
  creditTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800" },
  emptyConversation: { alignItems: "center", flex: 1, gap: tokens.spacing.md, justifyContent: "center", minHeight: 320, paddingHorizontal: tokens.spacing.xl },
  emptyCopy: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 24, textAlign: "center" },
  emptyIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.pill, height: 52, justifyContent: "center", width: 52 },
  emptyTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: "800", textAlign: "center" },
  notices: { gap: tokens.spacing.sm },
  screen: { gap: 0, paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 },
  thinking: { alignItems: "center", alignSelf: "flex-start", flexDirection: "row", gap: tokens.spacing.sm, paddingVertical: tokens.spacing.sm },
  thinkingText: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
});
