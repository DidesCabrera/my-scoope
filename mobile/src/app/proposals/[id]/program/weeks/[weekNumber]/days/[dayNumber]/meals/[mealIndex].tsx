import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback } from "react";

import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels } from "@/components/panels";
import { ProposalFoodCard, proposalPreviewAdapters } from "@/components/proposals/proposal-preview";
import { useProposalDetail } from "@/components/proposals/use-proposal-detail";
import { EntityCardAction, InlineNotice, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

export default function ProposedProgramMealDetailScreen() {
  const router = useRouter();
  const { id, weekNumber, dayNumber, mealIndex } = useLocalSearchParams<{ id: string; weekNumber: string; dayNumber: string; mealIndex: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(id);
  const setHeaderPresentation = useHeaderPresentation();
  const week = Number(weekNumber);
  const day = Number(dayNumber);
  const index = Number(mealIndex);
  const programDay = proposal?.program?.days.find((item) => item.week_number === week && item.day_number === day);
  const item = Number.isInteger(index) ? programDay?.dailyplan.meals[index] : undefined;
  const fallback = `/proposals/${id}/program/weeks/${weekNumber}/days/${dayNumber}` as Href;

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback, mode: "back", title: "Comida propuesta" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [fallback, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo la comida propuesta…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !item ? <InlineNotice tone="warning">La comida propuesta no está disponible.</InlineNotice> : null}
      {item ? (
        <EntityDetailPage
          entity="meal"
          eyebrow={`Semana ${week} · Día ${day} · Comida ${index + 1}`}
          indicators={[
            { icon: "food", label: "alimentos", value: item.meal.foods.length },
            ...(item.hour ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: item.hour.slice(0, 5) }] : []),
          ]}
          nutrition={proposalPreviewAdapters.nutrition(item.meal.kpis)}
          title={item.meal.name || `Comida ${index + 1}`}>
          <EntityDetailSection detail={`${item.meal.foods.length} alimentos`} title="Composición">
            <FoodPanels
              items={proposalPreviewAdapters.foodPanelItems(item.meal)}
              onOpenItem={(food) => {
                const foodIndex = proposalPreviewAdapters.foodPanelItems(item.meal).findIndex((candidate) => candidate.id === food.id);
                if (foodIndex >= 0) router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${index}/foods/${foodIndex}` as Href);
              }}
            />
          </EntityDetailSection>
          <SectionDivider />
          <EntityDetailSection title="Detalle de cada Alimento">
            {item.meal.foods.map((food, foodIndex) => (
              <ProposalFoodCard
                actions={(
                  <EntityCardAction label={`Ver detalle de ${food.food_name}`} onPress={() => router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${index}/foods/${foodIndex}` as Href)} role="link">
                    <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                  </EntityCardAction>
                )}
                food={food}
                key={`${food.food_id}-${food.food_name}-${foodIndex}`}
                onOpen={() => router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${index}/foods/${foodIndex}` as Href)}
              />
            ))}
          </EntityDetailSection>
        </EntityDetailPage>
      ) : null}
    </Screen>
  );
}
