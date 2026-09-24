import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback } from "react";

import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { MealPanels } from "@/components/panels";
import { ProposalMealCard, proposalPreviewAdapters } from "@/components/proposals/proposal-preview";
import { useProposalDetail } from "@/components/proposals/use-proposal-detail";
import { EntityCardAction, InlineNotice, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

export default function ProposedProgramDayDetailScreen() {
  const router = useRouter();
  const { id, weekNumber, dayNumber } = useLocalSearchParams<{ id: string; weekNumber: string; dayNumber: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(id);
  const setHeaderPresentation = useHeaderPresentation();
  const week = Number(weekNumber);
  const day = Number(dayNumber);
  const programDay = proposal?.program?.days.find((item) => item.week_number === week && item.day_number === day);
  const dailyplan = programDay?.dailyplan;

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/proposals/${id}/program` as Href, mode: "back", title: "Plan diario propuesto" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo el plan diario propuesto…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !dailyplan ? <InlineNotice tone="warning">El plan diario propuesto no está disponible.</InlineNotice> : null}
      {dailyplan ? (
        <EntityDetailPage
          entity="dailyPlan"
          eyebrow={`Semana ${week} · Día ${day}`}
          indicators={[
            { icon: "meal", label: "comidas", value: dailyplan.meals.length },
            { icon: "food", label: "alimentos", value: dailyplan.meals.reduce((total, item) => total + item.meal.foods.length, 0) },
          ]}
          nutrition={proposalPreviewAdapters.nutrition(dailyplan.kpis)}
          title={dailyplan.name || `Plan diario ${day}`}>
          <EntityDetailSection detail={`${dailyplan.meals.length} comidas`} title="Composición">
            <MealPanels
              items={proposalPreviewAdapters.mealPanelItems(dailyplan)}
              onOpenItem={(item) => router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${item.id}` as Href)}
            />
          </EntityDetailSection>
          <SectionDivider />
          <EntityDetailSection title="Detalle de cada Comida">
            {dailyplan.meals.map((item, mealIndex) => (
              <ProposalMealCard
                actions={(
                  <EntityCardAction label={`Ver detalle de ${item.meal.name}`} onPress={() => router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${mealIndex}` as Href)} role="link">
                    <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                  </EntityCardAction>
                )}
                eyebrow={`Comida ${mealIndex + 1}`}
                key={`${item.hour}-${item.meal.name}-${mealIndex}`}
                meal={item.meal}
                onOpenFood={(foodIndex) => router.push(`/proposals/${id}/program/weeks/${week}/days/${day}/meals/${mealIndex}/foods/${foodIndex}` as Href)}
                time={item.hour}
              />
            ))}
          </EntityDetailSection>
        </EntityDetailPage>
      ) : null}
    </Screen>
  );
}
