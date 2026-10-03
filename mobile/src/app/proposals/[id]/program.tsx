import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, View } from "react-native";

import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalProgramPreview } from "@/components/proposals/proposal-program-preview";
import { ProposalProgramActions } from "@/components/proposals";
import { useProposalDetail } from "@/components/proposals/use-proposal-detail";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

export default function ProposedProgramDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(id);
  const setHeaderPresentation = useHeaderPresentation();
  const [actionsVisible, setActionsVisible] = useState(false);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { icon: "more", label: "Acciones del programa propuesto", onPress: () => setActionsVisible(true) }, fallback: `/proposals/${id}` as Href, mode: "back", title: "Programa propuesto" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo el programa propuesto…" />;

  return (
    <Screen contentStyle={styles.screen} headerMode="preserve" scroll={false}>
      {error ? <View style={styles.notice}><RecoverableErrorState message={error} onRetry={() => void load()} /></View> : null}
      {proposal && !proposal.program ? <View style={styles.notice}><InlineNotice tone="warning">El programa propuesto no está disponible.</InlineNotice></View> : null}
      {proposal?.program ? (
        <ProposalProgramPreview
          onOpenDailyPlan={(week, day) => router.push(`/proposals/${proposal.id}/program/weeks/${week}/days/${day}` as Href)}
          onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)}
          onOpenMeal={(week, day, mealIndex) => router.push(`/proposals/${proposal.id}/program/weeks/${week}/days/${day}/meals/${mealIndex}` as Href)}
          program={proposal.program}
          scrollable
        />
      ) : null}
      <ProposalProgramActions
        onClose={() => setActionsVisible(false)}
        onOpenObjectives={() => router.push(`/proposals/${id}/program/objectives` as Href)}
        visible={actionsVisible}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  notice: { marginHorizontal: tokens.spacing.screen, marginTop: tokens.spacing.lg },
  screen: { gap: 0, paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 },
});
