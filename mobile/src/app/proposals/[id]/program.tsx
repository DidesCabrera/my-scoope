import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback } from "react";

import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalProgramPreview } from "@/components/proposals/proposal-program-preview";
import { useProposalDetail } from "@/components/proposals/use-proposal-detail";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";

export default function ProposedProgramDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(id);
  const setHeaderPresentation = useHeaderPresentation();

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/proposals/${id}` as Href, mode: "back", title: "Programa propuesto" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo el programa propuesto…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !proposal.program ? <InlineNotice tone="warning">El programa propuesto no está disponible.</InlineNotice> : null}
      {proposal?.program ? (
        <ProposalProgramPreview
          onOpenDailyPlan={(week, day) => router.push(`/proposals/${proposal.id}/program/weeks/${week}/days/${day}` as Href)}
          onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)}
          onOpenMeal={(week, day, mealIndex) => router.push(`/proposals/${proposal.id}/program/weeks/${week}/days/${day}/meals/${mealIndex}` as Href)}
          program={proposal.program}
        />
      ) : null}
    </Screen>
  );
}
