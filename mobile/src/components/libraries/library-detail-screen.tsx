import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { LibraryActionResult, LibraryItem } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { EntityDetailMetadata, EntityDetailPage, EntityDetailSection } from "@/components/details";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { Button, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";

import { DailyPlanMealCards, ProgramPanels } from "./entity-panels";
import { libraryDate, libraryNutrition } from "./presentation-adapters";
import { ProgramDetailPreview } from "./program-detail-preview";
import { LibraryActions } from "./library-actions";

const sectionTitles = { foods: "Tabla de comparación entre alimentos", meals: "Tabla de comparación entre comidas", weeks: "Semanas del programa" } as const;

function foodPanelItem(item: LibraryItem["panel"]["foods"][number]): FoodPanelItem {
  return { id: item.id, name: item.name, quantity: item.quantity, quantityUnit: item.quantity_unit, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function mealPanelItem(item: LibraryItem["panel"]["meals"][number]): MealPanelItem {
  return { id: item.id, name: item.name, time: item.time?.slice(0, 5), foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })), calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
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
  useFocusEffect(useCallback(() => { if (status === "authenticated" && id) void load(); }, [id, load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;
  const actionsModal = <LibraryActions apiRequest={apiRequest} entitySlug={entitySlug} item={item} onCompleted={handleActionCompleted} onVisibleChange={setActionsVisible} renderTrigger={() => null} visible={actionsVisible} />;
  if (item.entity === "program") {
    return <><ProgramDetailPreview
      footer={<>{item.can_calendarize ? <Button label="Calendarizar este programa" onPress={() => router.push(`/program/activate?programId=${item.id}` as Href)} /> : null}<EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /></>}
      item={item}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollable
    />{actionsModal}</>;
  }
  const panelCount = item.panel.kind === "foods" ? item.panel.foods.length : item.panel.kind === "meals" ? item.panel.meals.length : item.panel.kind === "weeks" ? item.panel.weeks.length : 0;
  const contextualDayId = Number(calendarizedDayId);
  return <><ScrollView contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }} scrollEventThrottle={16} style={styles.screen}><EntityDetailPage entity={item.entity} indicators={item.indicators} nutrition={libraryNutrition(item.nutrition)} subtitle={item.subtitle || undefined} title={item.name}>
    {item.panel.kind !== "none" ? <EntityDetailSection detail={`${panelCount} elementos`} title={sectionTitles[item.panel.kind]}>{item.panel.kind === "foods" ? <FoodPanels items={item.panel.foods.map(foodPanelItem)} /> : null}{item.panel.kind === "meals" ? <MealPanels items={item.panel.meals.map(mealPanelItem)} /> : null}{item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}</EntityDetailSection> : null}
    {item.entity === "meal" && Number.isInteger(contextualDayId) && contextualDayId > 0 && mealKey ? <MealAdherenceCheckIn dayId={contextualDayId} mealKey={mealKey} /> : null}
    {item.entity === "dailyPlan" && item.panel.kind === "meals" && item.panel.meals.length > 0 ? <EntityDetailSection detail={`${item.panel.meals.length} comidas`} title="Detalle de cada Comida"><DailyPlanMealCards items={item.panel.meals} /></EntityDetailSection> : null}
    {item.entity === "dailyPlan" && item.panel.foods.length > 0 ? <EntityDetailSection detail={`${item.panel.foods.length} alimentos`} title="Alimentos en este plan diario"><FoodPanels items={item.panel.foods.map(foodPanelItem)} /></EntityDetailSection> : null}
    <EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} />
  </EntityDetailPage></ScrollView>{actionsModal}</>;
}
const styles = StyleSheet.create({ screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 }, content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg }, loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen } });
