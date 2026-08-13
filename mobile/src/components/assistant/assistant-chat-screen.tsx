import * as Crypto from "expo-crypto";
import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, Text } from "react-native";

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
import { AppHeader, InlineNotice, LoadingState, Screen, textStyles } from "@/components/ui/primitives";

import { ChatComposer } from "./chat-composer";
import { ChatConversation } from "./chat-conversation";

export function AssistantChatScreen({ chatId, comparisonId = null }: { chatId: number | null; comparisonId?: number | null }) {
  const router = useRouter();
  const { status, apiRequest } = useSession();
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
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
      <Screen>
        <AppHeader eyebrow={chat ? chat.status_label : "Nueva conversación"} title={chat?.title ?? "Asistente AI"} />
        {availability ? <Text style={textStyles.caption}>{availability.available_credits} créditos disponibles</Text> : null}
        {unavailable ? <InlineNotice tone="warning">El Asistente no está disponible en este momento.</InlineNotice> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        {iterationWarning ? <InlineNotice tone="warning">La conversación se guardó, pero una iteración del plan requiere revisión.</InlineNotice> : null}
        {comparisonId ? <InlineNotice>Esta conversación usará la comparación guardada como contexto verificado.</InlineNotice> : null}
        {chat?.messages.length ? <ChatConversation messages={chat.messages} onPreparedAction={handlePreparedAction} /> : (
          <InlineNotice>Cuéntame qué quieres planificar o ajustar. El Asistente irá conservando esta conversación.</InlineNotice>
        )}
        {pending || sending ? <InlineNotice>El Asistente está procesando tu mensaje. Puedes salir; al volver recuperaremos este turno.</InlineNotice> : null}
        <ChatComposer
          disabled={unavailable || Boolean(pending)}
          loading={sending}
          maxLength={availability?.max_message_chars ?? 2000}
          onChangeText={setMessage}
          onSend={() => void send()}
          value={message}
        />
      </Screen>
    </KeyboardAvoidingView>
  );
}
