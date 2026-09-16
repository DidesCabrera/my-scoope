import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback } from "react";

import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { FoodDetailCardList } from "@/components/details/food-detail-card-list";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels } from "@/components/panels";
import { InlineNotice, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { sharedFoodPanelItems, sharedNutrition } from "@/sharing/presentation";
import { useSharedResource } from "@/sharing/use-shared-resource";

export default function SharedMealDetailScreen() {
  const router = useRouter();
  const { id, mealIndex } = useLocalSearchParams<{ id: string; mealIndex: string }>();
  const setHeaderPresentation = useHeaderPresentation();
  const { error, loading, resource } = useSharedResource(id);
  const index = Number(mealIndex);
  const meal = resource?.snapshot?.meals?.[index];
  const foods = meal ? sharedFoodPanelItems(meal) : [];
  const openFood = (food: (typeof foods)[number]) => {
    if (food.detailId == null) return;
    router.push(`/share/${id}/meals/${index}/foods/${food.detailId}` as Href);
  };

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/share/${id}` as Href, mode: "back", title: "Comida Compartida" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, setHeaderPresentation]));

  if (!id || !Number.isInteger(index) || index < 0) return <Redirect href="/inbox" />;
  return (
    <Screen headerMode="preserve">
      {loading ? <LoadingState label="Cargando comida compartida…" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!loading && resource && !meal ? <InlineNotice tone="error">La comida compartida no está disponible.</InlineNotice> : null}
      {meal ? (
        <EntityDetailPage
          entity="meal"
          eyebrow="Comida compartida"
          indicators={[
            { icon: "food", label: "alimentos", value: foods.length },
            ...(meal.time ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: meal.time.slice(0, 5) }] : []),
          ]}
          nutrition={sharedNutrition(meal.nutrition)}
          title={meal.name}>
          <EntityDetailSection detail={`${foods.length} alimentos`} title="Composición">
            <FoodPanels items={foods} onOpenItem={openFood} />
          </EntityDetailSection>
          {foods.length ? <>
            <SectionDivider />
            <EntityDetailSection title="Detalle de cada Alimento">
              <FoodDetailCardList
                items={foods}
                onOpenFood={openFood}
              />
            </EntityDetailSection>
          </> : null}
        </EntityDetailPage>
      ) : null}
    </Screen>
  );
}
