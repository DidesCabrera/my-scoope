import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";

import { EntityDetailPage } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { InlineNotice, LoadingState, Screen } from "@/components/ui";
import { sharedNutrition } from "@/sharing/presentation";
import { useSharedResource } from "@/sharing/use-shared-resource";

export default function SharedFoodDetailScreen() {
  const { id, mealIndex, foodIndex } = useLocalSearchParams<{ id: string; mealIndex: string; foodIndex: string }>();
  const setHeaderPresentation = useHeaderPresentation();
  const { error, loading, resource } = useSharedResource(id);
  const mealPosition = Number(mealIndex);
  const foodPosition = Number(foodIndex);
  const food = resource?.snapshot?.meals?.[mealPosition]?.foods?.[foodPosition];

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: `/share/${id}/meals/${mealIndex}` as Href, mode: "back", title: "Alimento Compartido" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [id, mealIndex, setHeaderPresentation]));

  if (!id || !Number.isInteger(mealPosition) || !Number.isInteger(foodPosition) || mealPosition < 0 || foodPosition < 0) return <Redirect href="/inbox" />;
  return (
    <Screen headerMode="preserve">
      {loading ? <LoadingState label="Cargando alimento compartido…" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {!loading && resource && !food ? <InlineNotice tone="error">El alimento compartido no está disponible.</InlineNotice> : null}
      {food ? (
        <EntityDetailPage
          entity="food"
          eyebrow="Alimento compartido"
          nutrition={sharedNutrition(food.nutrition)}
          subtitle={`${food.quantity_grams.toLocaleString("es-CL", { maximumFractionDigits: 1 })} g`}
          title={food.name}
        />
      ) : null}
    </Screen>
  );
}
