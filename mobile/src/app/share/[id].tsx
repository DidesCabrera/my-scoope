import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";

import type { ApiEnvelope, ShareClaimResult, ShareResource, SharingInboxData } from "@/api/types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels } from "@/components/panels";
import { Button, EntityCardAction, InlineNotice, LoadingState, Screen, SectionDivider } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";
import { sharedFoodPanelItems, sharedMealPanelItems, sharedNutrition } from "@/sharing/presentation";

type SavedShare = { entity: "dailyPlan" | "food" | "meal" | "program"; item_id: number };

const libraryPathByEntity: Record<SavedShare["entity"], string> = {
  dailyPlan: "daily-plans",
  food: "foods",
  meal: "meals",
  program: "programs",
};

export default function SharedResourceScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [resource, setResource] = useState<ShareResource | null>(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [inboxState, setInboxState] = useState<{ id: number; isSaved: boolean } | null>(null);
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

  useEffect(() => {
    if (!id || status !== "authenticated") return;
    let active = true;
    setInboxState(null);
    void apiRequest<SharingInboxData>("/api/v1/shares/inbox")
      .then((inbox) => {
        const item = inbox.items.find((candidate) => candidate.resource_id === id);
        if (active && item) setInboxState({ id: item.id, isSaved: item.is_saved });
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, [apiRequest, id, status]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/inbox", mode: "back", title: resource?.subject_type === "daily_plan" ? "Plan Diario Compartido" : "Contenido Compartido" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [resource?.subject_type, setHeaderPresentation]));

  if (!id) return <Redirect href="/today" />;

  const saveToLibrary = async () => {
    setClaiming(true);
    setError(null);
    try {
      const inboxItemId = inboxState?.id ?? (await apiRequest<ShareClaimResult>(`/api/v1/shares/${id}/claims`, { method: "POST" })).inbox_item_id;
      const saved = await apiRequest<SavedShare>(`/api/v1/shares/inbox/${inboxItemId}/save`, { method: "POST" });
      router.replace(`/libraries/${libraryPathByEntity[saved.entity]}/${saved.item_id}` as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setClaiming(false);
    }
  };

  const snapshot = resource?.snapshot;
  const meals = snapshot?.meals ?? [];
  const mealItems = snapshot ? sharedMealPanelItems(meals, snapshot.nutrition.calories) : [];
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
            nutrition={sharedNutrition(snapshot.nutrition)}
            title={resource.title}>
            <EntityDetailSection detail={`${meals.length} comidas`} title="Composición">
              <MealPanels items={mealItems} onOpenItem={(item) => router.push(`/share/${id}/meals/${item.id}` as Href)} />
            </EntityDetailSection>
            {meals.length ? <>
              <SectionDivider />
              <EntityDetailSection title="Detalle de cada Comida">
                {meals.map((meal, index) => (
                  <NutritionEntityCard
                    actions={(
                      <EntityCardAction label={`Ver detalle de ${meal.name}`} onPress={() => router.push(`/share/${id}/meals/${index}` as Href)} role="link">
                        <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                      </EntityCardAction>
                    )}
                    entity="meal"
                    eyebrow={`Comida ${index + 1}`}
                    indicators={[
                      { icon: "food", label: "alimentos", value: meal.foods.length },
                      ...(meal.time ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: meal.time.slice(0, 5) }] : []),
                    ]}
                    key={`${meal.name}-${index}`}
                    nutrition={sharedNutrition(meal.nutrition)}
                    title={meal.name}>
                    <FoodPanels items={sharedFoodPanelItems(meal)} />
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
        <Button
          label={inboxState?.isSaved ? "Abrir en mi biblioteca" : "Guardar en mi biblioteca"}
          loading={claiming}
          onPress={() => void saveToLibrary()}
          variant={inboxState?.isSaved ? "secondary" : "primary"}
        />
      ) : null}
    </Screen>
  );
}
