import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ExternalLink } from "lucide-react-native";
import { useCallback } from "react";

import type { ProposalDetail, ProposalFood } from "@/api/types";
import { EntityDetailPage } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { EntityCardAction, InlineNotice, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";
import { proposalPreviewAdapters } from "./proposal-preview";
import { useProposalDetail } from "./use-proposal-detail";

type Context = "meal" | "dailyplan" | "program";

function integer(value: string | undefined): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function foodForContext(
  proposal: ProposalDetail | null,
  context: Context,
  params: { foodIndex: number | null; mealIndex: number | null; weekNumber: number | null; dayNumber: number | null },
): ProposalFood | undefined {
  if (!proposal || params.foodIndex == null) return undefined;
  if (context === "meal") return proposal.meal?.foods[params.foodIndex];
  if (context === "dailyplan" && params.mealIndex != null) {
    return proposal.dailyplan?.meals[params.mealIndex]?.meal.foods[params.foodIndex];
  }
  if (context === "program" && params.mealIndex != null && params.weekNumber != null && params.dayNumber != null) {
    const day = proposal.program?.days.find((item) => item.week_number === params.weekNumber && item.day_number === params.dayNumber);
    return day?.dailyplan.meals[params.mealIndex]?.meal.foods[params.foodIndex];
  }
  return undefined;
}

function fallbackForContext(context: Context, id: string, params: { mealIndex?: string; weekNumber?: string; dayNumber?: string }): Href {
  if (context === "meal") return `/proposals/${id}/entity` as Href;
  if (context === "dailyplan") return `/proposals/${id}/entity/meals/${params.mealIndex}` as Href;
  return `/proposals/${id}/program/weeks/${params.weekNumber}/days/${params.dayNumber}/meals/${params.mealIndex}` as Href;
}

export function ProposalFoodDetailRoute({ context }: { context: Context }) {
  const router = useRouter();
  const raw = useLocalSearchParams<{ id: string; foodIndex: string; mealIndex?: string; weekNumber?: string; dayNumber?: string }>();
  const { error, load, loading, proposal, status } = useProposalDetail(raw.id);
  const setHeaderPresentation = useHeaderPresentation();
  const fallback = fallbackForContext(context, raw.id, raw);
  const food = foodForContext(proposal, context, {
    foodIndex: integer(raw.foodIndex),
    mealIndex: integer(raw.mealIndex),
    weekNumber: integer(raw.weekNumber),
    dayNumber: integer(raw.dayNumber),
  });

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback, mode: "back", title: "Alimento propuesto" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [fallback, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !proposal) return <LoadingState label="Abriendo el alimento propuesto…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {proposal && !food ? <InlineNotice tone="warning">El alimento propuesto no está disponible.</InlineNotice> : null}
      {food ? (
        <EntityDetailPage
          action={food.food_id ? (
            <EntityCardAction label="Abrir alimento en la biblioteca" onPress={() => router.push(`/libraries/foods/${food.food_id}` as Href)} role="link">
              <ExternalLink color={tokens.color.textMuted} size={20} strokeWidth={2.2} />
            </EntityCardAction>
          ) : undefined}
          entity="food"
          eyebrow="Alimento dentro de la propuesta"
          nutrition={proposalPreviewAdapters.foodNutrition(food)}
          subtitle={`${food.quantity ?? 0} ${food.unit || "g"}`}
          title={food.food_name || "Alimento"}
        />
      ) : null}
    </Screen>
  );
}
