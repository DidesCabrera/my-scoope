import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";

import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalProgramWeekObjectivesCard } from "@/components/proposals/proposal-program-preview";
import { useProposalDetail } from "@/components/proposals/use-proposal-detail";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";

export default function ProposalProgramObjectivesScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(id);
  const setHeaderPresentation = useHeaderPresentation();

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/proposals/${id}/program` as Href, forceFallback: true, mode: "back", title: "Objetivos por semana" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo los objetivos…" />;

  const program = proposal?.program;
  const weeks = program?.nutrition_specification?.weeks ?? [];
  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !proposal.program ? <InlineNotice tone="warning">El programa propuesto no está disponible.</InlineNotice> : null}
      {program && weeks.length === 0 ? <InlineNotice>Esta propuesta no contiene objetivos semanales.</InlineNotice> : null}
      {program ? weeks.map(({ week }) => <ProposalProgramWeekObjectivesCard key={week} program={program} week={week} />) : null}
    </Screen>
  );
}
