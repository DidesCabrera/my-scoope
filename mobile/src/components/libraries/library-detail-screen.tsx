import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CompositionMutationResult, LibraryActionResult, LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { EntityDetailMetadata, EntityDetailPage, EntityDetailSection } from "@/components/details";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { SectionDivider } from "@/components/ui";
import { Button, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

import { DailyPlanMealCards, ProgramPanels } from "./entity-panels";
import { libraryDate, libraryNutrition } from "./presentation-adapters";
import { ProgramDetailPreview } from "./program-detail-preview";
import { LibraryActions } from "./library-actions";
import { pickerHref } from "@/components/pickers/composition-picker-screen";

const sectionTitles = { foods: "Tabla de comparación entre alimentos", meals: "Tabla de comparación entre comidas", weeks: "Semanas del programa" } as const;

function foodPanelItem(item: LibraryItem["panel"]["foods"][number]): FoodPanelItem {
  return { id: item.id, relationId: item.relation_id, name: item.name, quantity: item.quantity, quantityUnit: item.quantity_unit, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function mealPanelItem(item: LibraryItem["panel"]["meals"][number]): MealPanelItem {
  return { id: item.id, relationId: item.relation_id, detailId: item.detail_id, name: item.name, time: item.time?.slice(0, 5), note: item.note, foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })), calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

export function LibraryDetailScreen({ entitySlug }: { entitySlug: "foods" | "meals" | "daily-plans" | "programs" }) {
  const router = useRouter();
  const { id, calendarizedDayId, mealKey } = useLocalSearchParams<{ id: string; calendarizedDayId?: string; mealKey?: string }>();
  const { status, apiRequest } = useSession();
  const [item, setItem] = useState<LibraryItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const headerEntity = entitySlug === "daily-plans" ? "dailyPlan" : entitySlug === "programs" ? "program" : entitySlug === "meals" ? "meal" : "food";
  const fallbackTitle = entitySlug === "daily-plans" ? "Plan diario" : entitySlug === "programs" ? "Programa" : entitySlug === "meals" ? "Comida" : "Alimento";
  const openActions = useCallback(() => setActionsVisible(true), []);
  useFocusEffect(useCallback(() => { setHeaderPresentation({ mode: "library-detail", action: item?.actions?.length ? { label: `Más acciones para ${item.name}`, onPress: openActions } : undefined, entity: headerEntity, identityVisible: compactHeaderVisible, title: item?.name ?? fallbackTitle }); return () => setHeaderPresentation({ mode: "default" }); }, [compactHeaderVisible, fallbackTitle, headerEntity, item, openActions, setHeaderPresentation]));
  const load = useCallback(async () => { setLoading(true); setError(null); try { setItem(await apiRequest<LibraryItem>(`/api/v1/library/${entitySlug}/${id}`)); } catch (nextError) { setError(userFacingError(nextError)); } finally { setLoading(false); } }, [apiRequest, entitySlug, id]);
  const handleActionCompleted = useCallback((result: LibraryActionResult) => {
    if (result.action === "delete") {
      router.replace(`/libraries/${entitySlug}` as Href);
      return;
    }
    if (result.action === "duplicate") {
      router.push(`/libraries/${entitySlug}/${result.item_id}` as Href);
      return;
    }
    void load();
  }, [entitySlug, load, router]);
  const mutateComposition = useCallback(async (path: string, init: RequestInit) => {
    try {
      const result = await apiRequest<CompositionMutationResult>(path, init);
      await load();
      Alert.alert("Listo", result.message);
    } catch (nextError) {
      Alert.alert("No pudimos guardar el cambio", userFacingError(nextError));
      throw nextError;
    }
  }, [apiRequest, load]);
  useFocusEffect(useCallback(() => { if (status === "authenticated" && id) void load(); }, [id, load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;
  const actionsModal = <LibraryActions apiRequest={apiRequest} entitySlug={entitySlug} item={item} onCompleted={handleActionCompleted} onVisibleChange={setActionsVisible} renderTrigger={() => null} visible={actionsVisible} />;
  if (item.entity === "program") {
    return <><ProgramDetailPreview
      footer={<>{item.can_calendarize && !item.is_draft ? <Button label="Calendarizar este programa" onPress={() => router.push(`/program/activate?programId=${item.id}` as Href)} /> : null}<EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /></>}
      item={item}
      onAddWeek={item.can_calendarize ? () => router.push(`/pickers/week-to-program?programId=${item.id}` as Href) : undefined}
      onAssignDailyPlan={item.can_calendarize ? (week, day) => router.push(pickerHref("dailyplan-to-program", { programId: item.id, weekNumber: week, dayNumber: day })) : undefined}
      onDuplicateWeek={item.can_calendarize ? async (week) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}/duplicate`, { method: "POST" }); } : undefined}
      onRemoveDailyPlan={item.can_calendarize ? async (week, day) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}/days/${day}`, { method: "DELETE" }); } : undefined}
      onRemoveWeek={item.can_calendarize ? async (week) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}`, { method: "DELETE" }); } : undefined}
      onReorderWeeks={item.can_calendarize ? async (weeks) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: weeks }) }); } : undefined}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollable
    />{actionsModal}</>;
  }
  const panelCount = item.panel.kind === "foods" ? item.panel.foods.length : item.panel.kind === "meals" ? item.panel.meals.length : item.panel.kind === "weeks" ? item.panel.weeks.length : 0;
  const isEmptyDraft = item.is_draft && panelCount === 0 && (item.entity === "meal" || item.entity === "dailyPlan");
  const contextualDayId = Number(calendarizedDayId);
  const foodItems = item.panel.foods.map(foodPanelItem);
  const mealItems = item.panel.meals.map(mealPanelItem);
  const foodEditing = item.entity === "meal" ? {
    onDelete: async (food: FoodPanelItem) => { if (food.relationId) await mutateComposition(`/api/v1/library/meals/${item.id}/foods/${food.relationId}`, { method: "DELETE" }); },
    onReorder: async (foods: FoodPanelItem[]) => { await mutateComposition(`/api/v1/library/meals/${item.id}/foods/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: foods.map((food) => food.relationId) }) }); },
    onUpdateQuantity: async (food: FoodPanelItem, quantity: number) => { if (food.relationId) await mutateComposition(`/api/v1/library/meals/${item.id}/foods/${food.relationId}`, { method: "PATCH", body: JSON.stringify({ quantity }) }); },
  } : undefined;
  const mealEditing = item.entity === "dailyPlan" ? {
    onDelete: async (meal: MealPanelItem) => { if (meal.relationId) await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/${meal.relationId}`, { method: "DELETE" }); },
    onOpen: (meal: MealPanelItem) => { if (meal.detailId) router.push(`/libraries/meals/${meal.detailId}` as Href); },
    onReorder: async (meals: MealPanelItem[]) => { await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: meals.map((meal) => meal.relationId) }) }); },
    onReplace: (meal: MealPanelItem) => { if (meal.relationId) router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, dailyPlanMealId: meal.relationId })); },
  } : undefined;
  return <><ScrollView contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }} scrollEventThrottle={16} style={styles.screen}><EntityDetailPage entity={item.entity} indicators={isEmptyDraft ? undefined : item.indicators} nutrition={libraryNutrition(item.nutrition)} showNutrition={!isEmptyDraft} subtitle={item.subtitle || undefined} title={item.name}>
    {!isEmptyDraft && item.panel.kind !== "none" ? <EntityDetailSection detail={`${panelCount} elementos`} title={sectionTitles[item.panel.kind]}>{item.panel.kind === "foods" ? <FoodPanels editing={foodEditing} items={foodItems} /> : null}{item.panel.kind === "meals" ? <MealPanels editing={mealEditing} items={mealItems} /> : null}{item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}</EntityDetailSection> : null}
    {item.entity === "meal" ? <Button label="+ Agregar alimento" onPress={() => router.push(pickerHref("food-to-meal", { mealId: item.id }))} /> : null}
    {item.entity === "dailyPlan" ? <Button label="+ Agregar Comida" onPress={() => router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id }))} /> : null}
    {item.entity === "meal" && Number.isInteger(contextualDayId) && contextualDayId > 0 && mealKey ? <MealAdherenceCheckIn dayId={contextualDayId} mealKey={mealKey} /> : null}
    {item.entity === "dailyPlan" && item.panel.kind === "meals" && item.panel.meals.length > 0 ? <><SectionDivider /><EntityDetailSection detail={`${item.panel.meals.length} comidas`} title="Detalle de cada Comida"><DailyPlanMealCards items={item.panel.meals} onRemove={async (meal) => { if (meal.relation_id) await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/${meal.relation_id}`, { method: "DELETE" }); }} /></EntityDetailSection></> : null}
    {item.entity === "dailyPlan" && item.panel.foods.length > 0 ? <><SectionDivider /><EntityDetailSection detail={`${item.panel.foods.length} alimentos`} title="Alimentos en este plan diario"><FoodPanels items={item.panel.foods.map(foodPanelItem)} /></EntityDetailSection></> : null}
    {!isEmptyDraft ? <EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /> : null}
  </EntityDetailPage></ScrollView>{actionsModal}</>;
}
const styles = StyleSheet.create({ screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 }, content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg }, loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen } });
