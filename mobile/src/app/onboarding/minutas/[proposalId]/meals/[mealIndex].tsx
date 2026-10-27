import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels } from "@/components/panels";
import { proposalPreviewAdapters } from "@/components/proposals/proposal-preview";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { HeaderMetadataChip, InlineNotice, LoadingState, Screen } from "@/components/ui";

export default function OnboardingMealDetailScreen() {
  const { proposalId, mealIndex } = useLocalSearchParams<{ proposalId: string; mealIndex: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!proposalId) return;
    setLoading(true);
    setError(null);
    try {
      setProposal(await apiRequest<ProposalDetail>(`/api/v1/proposals/${proposalId}`));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, proposalId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/onboarding" as Href, mode: "back", title: "Comida propuesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo la comida propuesta…" />;

  const index = Number(mealIndex);
  const item = Number.isInteger(index) && index >= 0 ? proposal?.dailyplan?.meals[index] : undefined;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !item ? <InlineNotice tone="warning">La comida propuesta no está disponible.</InlineNotice> : null}
      {item ? (
        <EntityDetailPage
          entity="meal"
          eyebrow={`Comida ${index + 1}`}
          eyebrowAccessory={item.hour ? <HeaderMetadataChip kind="time" value={item.hour.slice(0, 5)} /> : undefined}
          indicators={[{ icon: "food", label: "alimentos", value: item.meal.foods.length }]}
          nutrition={proposalPreviewAdapters.nutrition(item.meal.kpis)}
          title={item.meal.name || `Comida ${index + 1}`}>
          <EntityDetailSection detail={`${item.meal.foods.length} alimentos`} title="Composición">
            <FoodPanels items={proposalPreviewAdapters.foodPanelItems(item.meal)} />
          </EntityDetailSection>
        </EntityDetailPage>
      ) : null}
    </Screen>
  );
}
