import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Carrot, ChevronRight, ClipboardList, LayoutGrid, Rows3, Utensils } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";

import type { ApiEnvelope, ComparisonKind, ComparisonResultItem, ShareClaimResult, ShareResource, SharingInboxData } from "@/api/types";
import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { EntityDetailPage, EntityDetailSection } from "@/components/details/entity-detail-page";
import { FoodDetailCardList } from "@/components/details/food-detail-card-list";
import { ComparisonItemsSummary, SavedComparisonPreviewPanels } from "@/components/comparisons";
import { ComparisonResultCards } from "@/components/comparisons/comparison-result";
import { ProgramDetailPreview } from "@/components/libraries/program-detail-preview";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { ProgramSectionHeader } from "@/components/programs/program-section-header";
import { FoodPanels, GroupedFoodsCard, MealPanels } from "@/components/panels";
import { SharedResourceActions } from "@/components/sharing/shared-resource-actions";
import { AppHeader, Button, Chip, DistributedTabBar, EntityCardAction, EntityIcon, HeaderMetadataChip, InlineNotice, LoadingState, NutritionFactsCard, Screen, type EntityKind } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";
import { sharedComparisonResult, sharedFoodPanelItems, sharedMealPanelItems, sharedNutrition, sharedNutritionFacts, sharedPlanFoodPanelItems, sharedProgramLibraryItem, type ShareMeal } from "@/sharing/presentation";

type SavedShare = { entity: "comparison" | "dailyPlan" | "food" | "meal" | "program"; item_id: number };
type SharedComparisonTab = "cards" | "table" | "entities";

const comparisonEntityByKind = {
  dailyplans: "dailyPlan",
  foods: "food",
  meals: "meal",
} as const satisfies Record<ComparisonKind, Extract<EntityKind, "dailyPlan" | "food" | "meal">>;

const comparisonCountLabels = {
  dailyplans: ["Plan diario", "Planes diarios"],
  foods: ["Alimento", "Alimentos"],
  meals: ["Comida", "Comidas"],
} as const satisfies Record<ComparisonKind, readonly [string, string]>;

const comparisonTabIcons = { dailyplans: ClipboardList, foods: Carrot, meals: Utensils } as const;

function comparisonItemNutrition(item: ComparisonResultItem) {
  const calories = item.values.calories;
  const proteinAllocation = calories > 0 ? item.values.protein_g * 4 * 100 / calories : 0;
  const carbsAllocation = calories > 0 ? item.values.carbs_g * 4 * 100 / calories : 0;
  const fatAllocation = calories > 0 ? item.values.fat_g * 9 * 100 / calories : 0;
  return {
    calories,
    protein: { allocation: proteinAllocation, grams: item.values.protein_g, perKilogram: item.values.protein_per_kilogram },
    carbs: { allocation: carbsAllocation, grams: item.values.carbs_g },
    fat: { allocation: fatAllocation, grams: item.values.fat_g },
  };
}

const libraryPathByEntity: Record<SavedShare["entity"], string> = {
  comparison: "",
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
  const [actionsVisible, setActionsVisible] = useState(false);
  const [comparisonTab, setComparisonTab] = useState<SharedComparisonTab>("cards");
  const [inboxState, setInboxState] = useState<{ id: number; isSaved: boolean; resourceId: string } | null>(null);
  const [isOwnedResource, setIsOwnedResource] = useState(false);
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
    void Promise.all([
      apiRequest<SharingInboxData>("/api/v1/shares/inbox"),
      apiRequest<SharingInboxData>("/api/v1/shares/inbox?scope=sent"),
    ])
      .then(([inbox, sent]) => {
        const item = inbox.items.find((candidate) => candidate.resource_id === id);
        if (active && item) setInboxState({ id: item.id, isSaved: item.is_saved, resourceId: id });
        if (active) setIsOwnedResource(sent.items.some((candidate) => candidate.resource_id === id));
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, [apiRequest, id, status]);

  useFocusEffect(useCallback(() => {
    const headerTitle = resource?.subject_type === "comparison" ? "Comparación Compartida" : resource?.subject_type === "daily_plan" ? "Plan Diario Compartido" : resource?.subject_type === "food" ? "Alimento Compartido" : resource?.subject_type === "meal" ? "Comida Compartida" : resource?.subject_type === "program" ? "Programa Compartido" : "Contenido Compartido";
    setHeaderPresentation({ action: resource ? { icon: "more", label: `Acciones para ${resource.title}`, onPress: () => setActionsVisible(true) } : undefined, fallback: "/inbox", mode: "back", title: headerTitle });
    return () => setHeaderPresentation({ mode: "default" });
  }, [resource, setHeaderPresentation]));

  if (!id) return <Redirect href="/today" />;

  const saveToLibrary = async () => {
    setClaiming(true);
    setError(null);
    try {
      const inboxItemId = inboxState?.resourceId === id ? inboxState.id : (await apiRequest<ShareClaimResult>(`/api/v1/shares/${id}/claims`, { method: "POST" })).inbox_item_id;
      const saved = await apiRequest<SavedShare>(`/api/v1/shares/inbox/${inboxItemId}/save`, { method: "POST" });
      router.replace((saved.entity === "comparison" ? `/comparator/saved/${saved.item_id}` : `/libraries/${libraryPathByEntity[saved.entity]}/${saved.item_id}`) as Href);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setClaiming(false);
    }
  };

  const snapshot = resource?.snapshot;
  const meals = snapshot?.meals ?? [];
  const mealItems = snapshot ? sharedMealPanelItems(meals, snapshot.nutrition.calories) : [];
  const planFoodItems = snapshot ? sharedPlanFoodPanelItems(meals, snapshot.nutrition.calories) : [];
  const sharedComparison = snapshot ? sharedComparisonResult(snapshot) : null;
  const comparisonEntity = sharedComparison ? comparisonEntityByKind[sharedComparison.kind] : null;
  const ComparisonTabIcon = sharedComparison ? comparisonTabIcons[sharedComparison.kind] : Carrot;
  const comparisonCountLabel = sharedComparison
    ? comparisonCountLabels[sharedComparison.kind][sharedComparison.items.length === 1 ? 0 : 1]
    : "Elementos";
  const sharedProgram = snapshot && resource?.subject_type === "program" ? sharedProgramLibraryItem(snapshot, resource.title) : null;
  const sharedMeal: ShareMeal | null = snapshot && resource?.subject_type === "meal" ? {
    foods: snapshot.foods ?? [],
    name: resource.title,
    nutrition: snapshot.nutrition,
    time: snapshot.time,
  } : null;
  const sharedMealFoods = sharedMeal ? sharedFoodPanelItems(sharedMeal) : [];
  const isSaved = inboxState?.resourceId === id && inboxState.isSaved;
  const libraryAction = snapshot ? status === "anonymous" ? (
    <Button label="Iniciar sesión para agregar" onPress={() => router.push({ pathname: "/login", params: { returnTo: `/share/${id}` } })} />
  ) : isOwnedResource ? (
    <InlineNotice>Este contenido ya pertenece a tu biblioteca.</InlineNotice>
  ) : resource?.claim_policy === "none" ? (
    <InlineNotice>Este enlace es sólo de lectura.</InlineNotice>
  ) : (
    <Button
      label={isSaved ? "Abrir en mi biblioteca" : "Guardar en mi biblioteca"}
      loading={claiming}
      onPress={() => void saveToLibrary()}
      variant={isSaved ? "secondary" : "primary"}
    />
  ) : null;
  return (
    <>
    <Screen
      contentStyle={sharedProgram ? styles.programContent : loading ? styles.loadingContent : undefined}
      headerMode="preserve"
      scroll={!sharedProgram}
      scrollHeader={sharedComparison && comparisonEntity ? <View style={styles.comparisonHeader}>
        <AppHeader eyebrow={`Comparación ${sharedComparison.kind_label}`} eyebrowIcon={<EntityIcon entity={comparisonEntity} size="compact" />} title={resource?.title ?? "Comparación compartida"} />
        <Chip
          backgroundColor={`${tokens.color[comparisonEntity]}1A`}
          borderColor={tokens.color[comparisonEntity]}
          label={`${sharedComparison.items.length} ${comparisonCountLabel}`}
          textColor={tokens.color.textMain}
        />
        <ComparisonItemsSummary items={sharedComparison.items} />
      </View> : undefined}
      stickyHeader={sharedComparison && comparisonEntity ? <View style={styles.tabsBleed}>
        <DistributedTabBar<SharedComparisonTab>
          accessibilityLabel="Vista de la comparación compartida"
          activeTab={comparisonTab}
          onChange={setComparisonTab}
          tabs={[
            { icon: (selected) => <LayoutGrid color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "cards", label: "Cards" },
            { icon: (selected) => <Rows3 color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "table", label: "Tabla" },
            { icon: (selected) => <ComparisonTabIcon color={selected ? tokens.color.surfaceApp : tokens.color.textMuted} size={14} strokeWidth={2} />, key: "entities", label: sharedComparison.kind_label },
          ]}
        />
      </View> : undefined}
      stickyHeaderStyle={sharedComparison ? styles.stickyTabs : undefined}>
      {loading ? <LoadingState label="Cargando contenido compartido…" mode="content" /> : null}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {snapshot && resource?.subject_type === "daily_plan" ? (
        <>
          <EntityDetailPage
            entity="dailyPlan"
            eyebrow="Plan diario"
            indicators={[
              { icon: "meal", label: "comidas", value: meals.length },
              { icon: "food", label: "alimentos", value: meals.reduce((total, meal) => total + meal.foods.length, 0) },
            ]}
            nutrition={sharedNutrition(snapshot.nutrition)}
            title={resource.title}>
            <EntityDetailSection detail={`${meals.length} comidas`} title="Composición plan diario">
              <MealPanels items={mealItems} onOpenItem={(item) => router.push(`/share/${id}/meals/${item.id}` as Href)} />
            </EntityDetailSection>
            {meals.length ? <>
              <ProgramSectionHeader icon={Utensils} subtitle="Revisa el detalle de comida en este plan diario. Conoce sus alimentos, compáralos, y ve su impacto real en la comida." title="Detalle de cada Comida" />
                {meals.map((meal, index) => {
                  const openDetail = () => router.push(`/share/${id}/meals/${index}` as Href);
                  return <NutritionEntityCard
                    actions={(
                      <EntityCardAction label={`Ver detalle de ${meal.name}`} onPress={openDetail} role="link">
                        <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                      </EntityCardAction>
                    )}
                    entity="meal"
                    eyebrow={`Comida ${index + 1}`}
                    headingLink={{ label: `Ver detalle de ${meal.name}`, onPress: openDetail }}
                    indicators={[
                      { icon: "food", label: "alimentos", value: meal.foods.length },
                      ...(meal.time ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: meal.time.slice(0, 5) }] : []),
                    ]}
                    key={`${meal.name}-${index}`}
                    nutrition={sharedNutrition(meal.nutrition)}
                    title={meal.name}>
                    <FoodPanels
                      items={sharedFoodPanelItems(meal)}
                      onOpenItem={(food) => { if (food.detailId != null) router.push(`/share/${id}/meals/${index}/foods/${food.detailId}` as Href); }}
                    />
                  </NutritionEntityCard>;
                })}
            </> : null}
            {planFoodItems.length ? <>
              <ProgramSectionHeader icon={Carrot} subtitle="Aquí puedes revisar el aporte nutricional diario de cada alimento y evaluar su impacto contextual." title="Alimentos en este plan diario" />
              <GroupedFoodsCard items={planFoodItems} title="Alimentos plan diario" />
            </> : null}
          </EntityDetailPage>
        </>
      ) : null}
      {sharedProgram ? <ProgramDetailPreview footer={libraryAction} item={sharedProgram} scrollable showWeekAnalytics={false} /> : null}
      {snapshot && resource?.subject_type === "food" ? <EntityDetailPage
        entity="food"
        eyebrow="Alimento"
        nutrition={sharedNutrition(snapshot.nutrition)}
        subtitle={`${snapshot.summary.basis_grams ?? 100} ${snapshot.summary.basis_unit ?? "g"}`}
        title={resource.title}>
        <NutritionFactsCard
          facts={sharedNutritionFacts(snapshot.nutrition)}
          portion={{ quantity: null, unit: snapshot.summary.basis_unit ?? "g" }}
        />
      </EntityDetailPage> : null}
      {sharedMeal ? <EntityDetailPage
        entity="meal"
        eyebrow="Comida"
        eyebrowAccessory={sharedMeal.time ? <HeaderMetadataChip kind="time" value={sharedMeal.time.slice(0, 5)} /> : undefined}
        indicators={[{ icon: "food", label: "alimentos", value: sharedMealFoods.length }]}
        nutrition={sharedNutrition(sharedMeal.nutrition)}
        title={sharedMeal.name}>
        <EntityDetailSection detail={`${sharedMealFoods.length} alimentos`} title="Composición comida">
          <FoodPanels items={sharedMealFoods} onOpenItem={(food) => { if (food.detailId != null) router.push(`/share/${id}/foods/${food.detailId}` as Href); }} />
        </EntityDetailSection>
        {sharedMealFoods.length ? <>
          <ProgramSectionHeader icon={Carrot} subtitle="Familiarízate con los alimentos que conforman tu comida y determina su relevancia e impacto." title="Detalle de cada Alimento" />
          <FoodDetailCardList items={sharedMealFoods} onOpenFood={(food) => { if (food.detailId != null) router.push(`/share/${id}/foods/${food.detailId}` as Href); }} />
        </> : null}
      </EntityDetailPage> : null}
      {sharedComparison && comparisonEntity && comparisonTab === "cards" ? <ComparisonResultCards hideHeader interactive={false} result={sharedComparison} /> : null}
      {sharedComparison && comparisonEntity && comparisonTab === "table" ? <SavedComparisonPreviewPanels items={sharedComparison.items} scope={comparisonEntity} /> : null}
      {sharedComparison && comparisonEntity && comparisonTab === "entities" ? sharedComparison.items.map((item, index) => (
        <NutritionEntityCard
          entity={comparisonEntity}
          eyebrow={`${comparisonCountLabels[sharedComparison.kind][0]} ${index + 1}`}
          key={`${item.id}-${index}`}
          nutrition={comparisonItemNutrition(item)}
          subtitle={sharedComparison.kind === "foods" && item.quantity != null ? `${item.quantity} ${item.quantity_unit ?? "g"}` : undefined}
          title={item.name}
        />
      )) : null}
      {!sharedProgram ? libraryAction : null}
    </Screen>
    <SharedResourceActions onOpenInformation={() => router.push(`/share/${id}/information` as Href)} onVisibleChange={setActionsVisible} title={resource?.title ?? "Elemento compartido"} visible={actionsVisible} />
    </>
  );
}

const styles = StyleSheet.create({
  comparisonHeader: { gap: tokens.spacing.sm },
  loadingContent: { paddingBottom: 0, paddingTop: 0 },
  programContent: { gap: 0, paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 },
  stickyTabs: { paddingTop: tokens.spacing.xl },
  tabsBleed: { alignSelf: "stretch", marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding },
});
