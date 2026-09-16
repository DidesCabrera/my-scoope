import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels, MealPanels } from "@/components/panels";
import { ProposalFoodCard, ProposalMealCard, proposalPreviewAdapters } from "@/components/proposals/proposal-preview";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { EntityCardAction, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function ProposalEntityDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const headerTitle = proposal?.dailyplan ? "Plan Diario Propuesto" : proposal?.meal ? "Comida Propuesta" : "Detalle de Propuesta";

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
    setHeaderPresentation({ fallback: `/proposals/${id}` as Href, mode: "back", title: headerTitle });
    return () => setHeaderPresentation({ mode: "default" });
  }, [headerTitle, id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo la entidad propuesta…" />;

  const applied = proposal?.applied_result;
  const libraryHref = applied?.object_id && applied.kind
    ? (applied.kind === "meal" ? `/libraries/meals/${applied.object_id}` : `/libraries/daily-plans/${applied.object_id}`) as Href
    : null;
  const libraryAction = libraryHref ? (
    <EntityCardAction label="Abrir entidad en la biblioteca" onPress={() => router.push(libraryHref)} role="link">
      <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
    </EntityCardAction>
  ) : undefined;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal?.meal ? (
        <EntityDetailPage
          action={libraryAction}
          entity="meal"
          eyebrow="Comida propuesta"
          indicators={[{ icon: "food", label: "alimentos", value: proposal.meal.foods.length }]}
          nutrition={proposalPreviewAdapters.nutrition(proposal.meal.kpis)}
          title={proposal.meal.name || "Comida"}>
          <EntityDetailSection detail={`${proposal.meal.foods.length} alimentos`} title="Composición">
            <FoodPanels
              items={proposalPreviewAdapters.foodPanelItems(proposal.meal)}
              onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }}
            />
          </EntityDetailSection>
          {proposal.meal.foods.length ? (
            <>
              <SectionDivider />
              <EntityDetailSection title="Detalle de cada Alimento">
                {proposal.meal.foods.map((food, index) => (
                  <ProposalFoodCard
                    actions={food.food_id ? (
                      <EntityCardAction label={`Ver detalle de ${food.food_name}`} onPress={() => router.push(`/libraries/foods/${food.food_id}` as Href)} role="link">
                        <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                      </EntityCardAction>
                    ) : undefined}
                    food={food}
                    key={`${food.food_id}-${food.food_name}-${index}`}
                  />
                ))}
              </EntityDetailSection>
            </>
          ) : null}
        </EntityDetailPage>
      ) : null}
      {proposal?.dailyplan ? (
        <EntityDetailPage
          action={libraryAction}
          entity="dailyPlan"
          eyebrow="Plan diario propuesto"
          indicators={[
            { icon: "meal", label: "comidas", value: proposal.dailyplan.meals.length },
            { icon: "food", label: "alimentos", value: proposal.dailyplan.meals.reduce((total, item) => total + item.meal.foods.length, 0) },
          ]}
          nutrition={proposalPreviewAdapters.nutrition(proposal.dailyplan.kpis)}
          title={proposal.dailyplan.name || "Plan diario"}>
          <EntityDetailSection detail={`${proposal.dailyplan.meals.length} comidas`} title="Composición">
            <MealPanels
              items={proposalPreviewAdapters.mealPanelItems(proposal.dailyplan)}
              onOpenItem={(item) => router.push(`/proposals/${proposal.id}/entity/meals/${item.id}` as Href)}
            />
          </EntityDetailSection>
          <SectionDivider />
          <EntityDetailSection title="Detalle de cada Comida">
            {proposal.dailyplan.meals.map((item, index) => (
              <ProposalMealCard
                actions={(
                  <EntityCardAction label={`Ver detalle de ${item.meal.name}`} onPress={() => router.push(`/proposals/${proposal.id}/entity/meals/${index}` as Href)} role="link">
                    <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                  </EntityCardAction>
                )}
                eyebrow={`Comida ${index + 1}`}
                key={`${item.hour}-${item.meal.name}-${index}`}
                meal={item.meal}
                onOpenFood={(foodId) => router.push(`/libraries/foods/${foodId}` as Href)}
                time={item.hour}
              />
            ))}
          </EntityDetailSection>
        </EntityDetailPage>
      ) : null}
      {proposal && !proposal.meal && !proposal.dailyplan ? <Redirect href={`/proposals/${proposal.id}` as Href} /> : null}
    </Screen>
  );
}
