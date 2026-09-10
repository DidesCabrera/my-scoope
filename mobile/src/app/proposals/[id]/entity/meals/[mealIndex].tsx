import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels } from "@/components/panels";
import { ProposalFoodCard, proposalPreviewAdapters } from "@/components/proposals/proposal-preview";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { EntityCardAction, InlineNotice, LoadingState, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function ProposedMealDetailScreen() {
  const router = useRouter();
  const { id, mealIndex } = useLocalSearchParams<{ id: string; mealIndex: string }>();
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
    setHeaderPresentation({ fallback: `/proposals/${id}/entity` as Href, mode: "back", title: "Comida propuesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo la comida propuesta…" />;

  const index = Number(mealIndex);
  const item = Number.isInteger(index) ? proposal?.dailyplan?.meals[index] : undefined;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !item ? <InlineNotice tone="warning">La comida propuesta no está disponible.</InlineNotice> : null}
      {item ? (
        <EntityDetailPage
          entity="meal"
          eyebrow={item.hour ? `${item.hour.slice(0, 5)} · Comida ${index + 1}` : `Comida ${index + 1}`}
          indicators={[{ icon: "food", label: "alimentos", value: item.meal.foods.length }]}
          nutrition={proposalPreviewAdapters.nutrition(item.meal.kpis)}
          subtitle={item.note || undefined}
          title={item.meal.name || `Comida ${index + 1}`}>
          <EntityDetailSection detail={`${item.meal.foods.length} alimentos`} title="Composición">
            <FoodPanels items={proposalPreviewAdapters.foodPanelItems(item.meal)} />
          </EntityDetailSection>
          <EntityDetailSection title="Detalle de cada Alimento">
            {item.meal.foods.map((food, foodIndex) => (
              <ProposalFoodCard
                actions={food.food_id ? (
                  <EntityCardAction label={`Ver detalle de ${food.food_name}`} onPress={() => router.push(`/libraries/foods/${food.food_id}` as Href)} role="link">
                    <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                  </EntityCardAction>
                ) : undefined}
                food={food}
                key={`${food.food_id}-${food.food_name}-${foodIndex}`}
              />
            ))}
          </EntityDetailSection>
        </EntityDetailPage>
      ) : null}
    </Screen>
  );
}
