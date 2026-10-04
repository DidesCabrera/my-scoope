import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Text } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ProposalListData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalListCard } from "@/components/proposals";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { LoadingState, Screen, textStyles } from "@/components/ui/primitives";

export default function ChatProposalsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const chatId = Number(id);
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [page, setPage] = useState<ProposalListData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPage(await apiRequest<ProposalListData>(`/api/v1/ai/chats/${chatId}/proposals?limit=50`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, chatId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/assistant/${chatId}`, mode: "back", title: "Propuestas del chat" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [chatId, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !page) return <LoadingState label="Cargando propuestas del chat…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {loading && page ? <Text style={textStyles.caption}>Actualizando…</Text> : null}
      {page?.items.length ? page.items.map((proposal) => (
        <ProposalListCard key={proposal.id} onPress={() => router.push(`/proposals/${proposal.id}` as Href)} proposal={proposal} />
      )) : !error && !loading ? (
        <EmptyState message="Las propuestas creadas en esta conversación aparecerán aquí." title="Este chat aún no tiene propuestas" />
      ) : null}
    </Screen>
  );
}
