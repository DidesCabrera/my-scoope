import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalFacts } from "@/components/proposals/proposal-preview";
import { LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";

export default function ProposalReviewFactsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setProposal(await apiRequest<ProposalDetail>(`/api/v1/proposals/${id}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/proposals/${id}` as Href, forceFallback: true, mode: "back", title: "Fichas de la propuesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo las fichas…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal ? (
        <>
          <ProposalFacts description="Valores que esta propuesta busca alcanzar." facts={proposal.target_facts} title="Objetivo" />
          <ProposalFacts description="Valores existentes antes de generar la propuesta." facts={proposal.current_facts} title="Punto de partida" />
          <ProposalFacts description="Comprobaciones realizadas antes de permitir que la propuesta se aplique." facts={proposal.validation_facts} title="Validación" />
        </>
      ) : null}
    </Screen>
  );
}
