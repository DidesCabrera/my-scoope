import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";

import type { ApiEnvelope, ShareClaimResult, ShareResource } from "@/api/types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { Button, InlineNotice, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { appConfig } from "@/config/app-config";

type ShareNutrition = NonNullable<ShareResource["snapshot"]>["nutrition"];
type ShareMeal = NonNullable<NonNullable<ShareResource["snapshot"]>["meals"]>[number];
type SavedShare = { entity: "dailyPlan" | "food" | "meal" | "program"; item_id: number };

const libraryPathByEntity: Record<SavedShare["entity"], string> = {
  dailyPlan: "daily-plans",
  food: "foods",
  meal: "meals",
  program: "programs",
};

function nutrition(values: ShareNutrition) {
  const calories = values.calories || values.protein_grams * 4 + values.carbs_grams * 4 + values.fat_grams * 9;
  return {
    calories,
    protein: { grams: values.protein_grams, allocation: calories > 0 ? values.protein_grams * 4 * 100 / calories : 0 },
    carbs: { grams: values.carbs_grams, allocation: calories > 0 ? values.carbs_grams * 4 * 100 / calories : 0 },
    fat: { grams: values.fat_grams, allocation: calories > 0 ? values.fat_grams * 9 * 100 / calories : 0 },
  };
}

function foodPanelItems(meal: ShareMeal): FoodPanelItem[] {
  return meal.foods.map((food, index) => {
    const item = nutrition(food.nutrition);
    return {
      id: `shared-food-${index}`,
      name: food.name,
      quantity: food.quantity_grams,
      quantityUnit: "g",
      calories: item.calories,
      calorieShare: meal.nutrition.calories > 0 ? item.calories * 100 / meal.nutrition.calories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}

function mealPanelItems(meals: ShareMeal[], planCalories: number): MealPanelItem[] {
  return meals.map((meal, index) => {
    const item = nutrition(meal.nutrition);
    return {
      id: String(index),
      name: meal.name,
      time: meal.time?.slice(0, 5) ?? undefined,
      foods: meal.foods.map((food) => ({ name: food.name, quantity: food.quantity_grams, quantityUnit: "g" })),
      calories: item.calories,
      calorieShare: planCalories > 0 ? item.calories * 100 / planCalories : 0,
      proteinGrams: item.protein.grams,
      carbsGrams: item.carbs.grams,
      fatGrams: item.fat.grams,
      proteinAllocation: item.protein.allocation,
      carbsAllocation: item.carbs.allocation,
      fatAllocation: item.fat.allocation,
    };
  });
}

export default function SharedResourceScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [resource, setResource] = useState<ShareResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let active = true;
    void fetch(`${appConfig.apiBaseUrl}/api/v1/shares/${id}`)
      .then(async (response) => {
        const payload = await response.json() as ApiEnvelope<ShareResource>;
        if (!response.ok || !payload.ok) throw new Error(payload.ok ? "share_unavailable" : payload.error.message);
        if (active) setResource(payload.data);
      })
      .catch((nextError) => { if (active) setError(userFacingError(nextError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/inbox", mode: "back", title: resource?.subject_type === "daily_plan" ? "Plan Diario Compartido" : "Contenido Compartido" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [resource?.subject_type, setHeaderPresentation]));

  if (!id) return <Redirect href="/today" />;

  const saveToLibrary = async () => {
    setClaiming(true);
    setError(null);
    try {
      const claim = await apiRequest<ShareClaimResult>(`/api/v1/shares/${id}/claims`, { method: "POST" });
      const saved = await apiRequest<SavedShare>(`/api/v1/shares/inbox/${claim.inbox_item_id}/save`, { method: "POST" });
      router.replace(`/libraries/${libraryPathByEntity[saved.entity]}/${saved.item_id}` as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setClaiming(false);
    }
  };

  const snapshot = resource?.snapshot;
  const meals = snapshot?.meals ?? [];
  const mealItems = snapshot ? mealPanelItems(meals, snapshot.nutrition.calories) : [];
  return (
    <Screen headerMode="preserve">
      {loading ? <LoadingState label="Cargando contenido compartido…" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {snapshot && resource?.subject_type === "daily_plan" ? (
        <>
          <EntityDetailPage
            entity="dailyPlan"
            eyebrow="Plan diario compartido"
            indicators={[
              { icon: "meal", label: "comidas", value: meals.length },
              { icon: "food", label: "alimentos", value: meals.reduce((total, meal) => total + meal.foods.length, 0) },
            ]}
            nutrition={nutrition(snapshot.nutrition)}
            title={resource.title}>
            <EntityDetailSection detail={`${meals.length} comidas`} title="Composición">
              <MealPanels items={mealItems} />
            </EntityDetailSection>
            {meals.length ? <>
              <SectionDivider />
              <EntityDetailSection title="Detalle de cada Comida">
                {meals.map((meal, index) => (
                  <NutritionEntityCard
                    entity="meal"
                    eyebrow={`Comida ${index + 1}`}
                    indicators={[
                      { icon: "food", label: "alimentos", value: meal.foods.length },
                      ...(meal.time ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: meal.time.slice(0, 5) }] : []),
                    ]}
                    key={`${meal.name}-${index}`}
                    nutrition={nutrition(meal.nutrition)}
                    title={meal.name}>
                    <FoodPanels items={foodPanelItems(meal)} />
                  </NutritionEntityCard>
                ))}
              </EntityDetailSection>
            </> : null}
          </EntityDetailPage>
        </>
      ) : null}
      {snapshot && resource?.subject_type !== "daily_plan" ? <InlineNotice>La vista detallada para este tipo de contenido aún no está disponible.</InlineNotice> : null}
      {snapshot ? status === "anonymous" ? (
        <Button label="Iniciar sesión para agregar" onPress={() => router.push({ pathname: "/login", params: { returnTo: `/share/${id}` } })} />
      ) : resource?.claim_policy === "none" ? (
        <InlineNotice>Este enlace es sólo de lectura.</InlineNotice>
      ) : (
        <Button label="Guardar en mi biblioteca" loading={claiming} onPress={() => void saveToLibrary()} />
      ) : null}
    </Screen>
  );
}
