import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, Image, StyleSheet, Text, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { userFacingError } from "@/api/errors";
import type { CompositionMutationResult, LibraryActionResult, LibraryItem, MealCheckInInput, MealExecutionItem, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MealAdherenceCheckIn, MealCompletionCard, MealNoteCard, useMealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { DailyMealCompletionCard } from "@/components/calendarization/meal-completion-summary";
import { normalizeMealExecution, normalizeMealExecutionItem } from "@/components/calendarization/meal-execution";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { EntityDetailMetadata, EntityDetailPage, EntityDetailSection, FoodDetailCardList } from "@/components/details";
import { FoodPanels, MealPanels, type FoodPanelItem, type MealPanelItem } from "@/components/panels";
import { pickerConfigureHref, pickerHref } from "@/components/pickers/composition-picker-screen";
import { MutationStatusModal, SectionDivider, type MutationStatus } from "@/components/ui";
import { Button, InlineNotice, textStyles } from "@/components/ui/primitives";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";
import type { FoodLabelImage } from "@/label-capture/types";
import { internalHref } from "@/navigation/internal-href";

import { DailyPlanMealCards, ProgramPanels } from "./entity-panels";
import { libraryDate, libraryNutrition } from "./presentation-adapters";
import { ProgramDetailPreview } from "./program-detail-preview";
import { LibraryActions } from "./library-actions";

const sectionTitles = { foods: "Tabla de comparación entre alimentos", meals: "Tabla de comparación entre comidas", weeks: "Semanas del programa" } as const;

function foodPanelItem(item: LibraryItem["panel"]["foods"][number]): FoodPanelItem {
  return { id: item.id, detailId: item.detail_id, relationId: item.relation_id, name: item.name, quantity: item.quantity, quantityUnit: item.quantity_unit, calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, proteinPerKilogram: item.protein_per_kilogram, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

function mealPanelItem(item: LibraryItem["panel"]["meals"][number]): MealPanelItem {
  return { id: item.id, relationId: item.relation_id, detailId: item.detail_id, name: item.name, time: item.time?.slice(0, 5), note: item.note, foods: item.foods.map((food) => ({ name: food.name, quantity: food.quantity, quantityUnit: food.quantity_unit })), calories: item.calories, calorieShare: item.calorie_share, proteinGrams: item.protein_grams, proteinPerKilogram: item.protein_per_kilogram, carbsGrams: item.carbs_grams, fatGrams: item.fat_grams, proteinAllocation: item.protein_allocation, carbsAllocation: item.carbs_allocation, fatAllocation: item.fat_allocation };
}

export function LibraryDetailScreen({ entitySlug }: { entitySlug: "foods" | "meals" | "daily-plans" | "programs" }) {
  const router = useRouter();
  const { id, calendarizedDayId, dailyPlanId, dailyPlanMealId, mealKey, mealTime, pinned, pickerEntryTo, pickerKind, pickerRelationId, pickerTargetId, returnTo } = useLocalSearchParams<{ id: string; calendarizedDayId?: string; dailyPlanId?: string; dailyPlanMealId?: string; mealKey?: string; mealTime?: string; pinned?: string; pickerEntryTo?: string; pickerKind?: string; pickerRelationId?: string; pickerTargetId?: string; returnTo?: string }>();
  const { status, apiRequest } = useSession();
  const [item, setItem] = useState<LibraryItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const setHeaderPresentation = useHeaderPresentation();
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionSheet, setActionSheet] = useState<"change-time" | "menu" | null>(null);
  const [panelTimeMeal, setPanelTimeMeal] = useState<MealPanelItem | null>(null);
  const [labelImage, setLabelImage] = useState<FoodLabelImage | null>(null);
  const [labelImageBusy, setLabelImageBusy] = useState(false);
  const [todayContext, setTodayContext] = useState<TodayData | null>(null);
  const [savingMealKey, setSavingMealKey] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<{ mealKey: string; message: string } | null>(null);
  const [pinnedMealExecution, setPinnedMealExecution] = useState<MealExecutionItem | null>(null);
  const [mutationStatus, setMutationStatus] = useState<MutationStatus | null>(null);
  const [contextTime, setContextTime] = useState(mealTime?.slice(0, 5) ?? "");
  const contextDailyPlanId = Number(dailyPlanId);
  const contextDailyPlanMealId = Number(dailyPlanMealId);
  const returnHref = internalHref(returnTo);
  const pickerEntryHref = internalHref(pickerEntryTo);
  const contextualPickerKind = pickerKind === "meal-to-dailyplan" || pickerKind === "meal-to-calendarized-day" ? pickerKind : null;
  const contextualPickerTargetId = Number(pickerTargetId);
  const contextualPickerRelationId = Number(pickerRelationId) || undefined;
  const createdMealId = Number(id);
  const isContextualMealCreation = entitySlug === "meals"
    && Boolean(returnHref)
    && Boolean(pickerEntryHref)
    && Boolean(contextualPickerKind)
    && Number.isInteger(contextualPickerTargetId)
    && contextualPickerTargetId > 0
    && Number.isInteger(createdMealId)
    && createdMealId > 0;
  const contextualDetailParams = new URLSearchParams();
  if (isContextualMealCreation && returnHref && pickerEntryHref && contextualPickerKind) {
    contextualDetailParams.set("pickerEntryTo", String(pickerEntryHref));
    contextualDetailParams.set("pickerKind", contextualPickerKind);
    if (contextualPickerRelationId) contextualDetailParams.set("pickerRelationId", String(contextualPickerRelationId));
    contextualDetailParams.set("pickerTargetId", String(contextualPickerTargetId));
    contextualDetailParams.set("returnTo", String(returnHref));
  }
  const currentDetailHref = (isContextualMealCreation
    ? `/libraries/meals/${id}?${contextualDetailParams.toString()}`
    : `/libraries/${entitySlug}/${id}`) as Href;
  const hasMealTimeContext = entitySlug === "meals"
    && Number.isInteger(contextDailyPlanId)
    && contextDailyPlanId > 0
    && Number.isInteger(contextDailyPlanMealId)
    && contextDailyPlanMealId > 0;
  const isPinnedMealContext = entitySlug === "meals" && pinned === "1" && Boolean(mealKey);
  const pinnedMealAdherence = useMealAdherenceCheckIn({ enabled: isPinnedMealContext, mealKey: mealKey ?? "", mode: "pinned", onChange: setPinnedMealExecution });
  const headerEntity = entitySlug === "daily-plans" ? "dailyPlan" : entitySlug === "programs" ? "program" : entitySlug === "meals" ? "meal" : "food";
  const fallbackTitle = entitySlug === "daily-plans" ? "Plan diario" : entitySlug === "programs" ? "Programa" : entitySlug === "meals" ? "Comida" : "Alimento";
  const isPinnedPlan = item?.entity === "dailyPlan" && todayContext?.calendarization == null && todayContext?.pinned_plan?.id === item.id;
  const openActions = useCallback(() => setActionSheet("menu"), []);
  const openTimeChange = useCallback(() => setActionSheet("change-time"), []);
  const setPinnedPlan = useCallback(async (nextPinned: boolean) => {
    if (!item || item.entity !== "dailyPlan") return;
    setError(null);
    try {
      const updated = await apiRequest<TodayData>("/api/v1/today/pinned-plan", nextPinned
        ? { body: JSON.stringify({ dailyplan_id: item.id }), method: "PUT" }
        : { method: "DELETE" });
      setTodayContext(updated);
    } catch (nextError) {
      setError(userFacingError(nextError));
    }
  }, [apiRequest, item]);
  const confirmPinnedPlan = useCallback((nextPinned: boolean) => {
    Alert.alert(
      nextPinned ? "¿Fijar este plan para hoy?" : "¿Dejar de fijar este plan?",
      nextPinned
        ? "Este plan diario aparecerá como tu Plan de hoy."
        : "El plan dejará de aparecer como tu Plan de hoy.",
      [
        { style: "cancel", text: "Cancelar" },
        { onPress: () => void setPinnedPlan(nextPinned), text: nextPinned ? "Fijar" : "Dejar de fijar" },
      ],
    );
  }, [setPinnedPlan]);
  const cancelContextualCreation = useCallback(() => { if (pickerEntryHref) router.dismissTo(pickerEntryHref); }, [pickerEntryHref, router]);
  const continueContextualCreation = useCallback(() => {
    if (!contextualPickerKind || !returnHref || !isContextualMealCreation) return;
    router.replace(pickerConfigureHref(contextualPickerKind, {
      relationId: contextualPickerRelationId,
      returnTo: returnHref,
      selectedId: createdMealId,
      targetId: contextualPickerTargetId,
      weekNumber: 1,
    }));
  }, [contextualPickerKind, contextualPickerRelationId, contextualPickerTargetId, createdMealId, isContextualMealCreation, returnHref, router]);
  useFocusEffect(useCallback(() => {
    if (isContextualMealCreation && pickerEntryHref) {
      setHeaderPresentation({
        mode: "back",
        action: { disabled: item?.is_draft !== false, label: "Listo", onPress: continueContextualCreation },
        fallback: pickerEntryHref,
        leadingAction: { label: "Cancelar", onPress: cancelContextualCreation },
        title: item?.name ?? fallbackTitle,
      });
    } else {
      setHeaderPresentation({
        mode: "library-detail",
        action: item?.actions?.length ? { label: `Más acciones para ${item?.name ?? fallbackTitle}`, onPress: openActions } : undefined,
        entity: headerEntity,
        identityVisible: compactHeaderVisible,
        secondaryAction: hasMealTimeContext
          ? { icon: "clock", label: "Cambiar hora", onPress: openTimeChange }
          : item?.entity === "dailyPlan" && todayContext?.calendarization == null
            ? { icon: "pin", label: isPinnedPlan ? "Dejar de fijar como Plan de hoy" : "Fijar como Plan de hoy", onPress: () => confirmPinnedPlan(!isPinnedPlan) }
            : item?.entity === "program" && item.can_calendarize && !item.is_draft
              ? { icon: "calendar-clock", label: "Calendarizar este programa", onPress: () => router.push(`/program/activate?programId=${item.id}` as Href) }
              : undefined,
        title: item?.name ?? fallbackTitle,
      });
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [cancelContextualCreation, compactHeaderVisible, confirmPinnedPlan, continueContextualCreation, fallbackTitle, hasMealTimeContext, headerEntity, isContextualMealCreation, isPinnedPlan, item, openActions, openTimeChange, pickerEntryHref, router, setHeaderPresentation, todayContext?.calendarization]));
  const load = useCallback(async () => { setLoading(true); setError(null); try {
    const [nextItem, nextToday] = await Promise.all([
      apiRequest<LibraryItem>(`/api/v1/library/${entitySlug}/${id}`),
      entitySlug === "daily-plans" || isPinnedMealContext ? apiRequest<TodayData>("/api/v1/today") : Promise.resolve(null),
    ]);
    setItem(nextItem);
    setTodayContext(nextToday);
  } catch (nextError) { setError(userFacingError(nextError)); } finally { setLoading(false); } }, [apiRequest, entitySlug, id, isPinnedMealContext]);
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
  const mutateComposition = useCallback(async (
    path: string,
    init: RequestInit,
    feedback?: Pick<MutationStatus, "loadingLabel" | "successLabel">,
  ) => {
    if (feedback) setMutationStatus({ ...feedback, phase: "loading" });
    try {
      const result = await apiRequest<CompositionMutationResult>(path, init);
      await load();
      if (feedback) setMutationStatus({ ...feedback, phase: "success" });
      else Alert.alert("Listo", result.message);
    } catch (nextError) {
      if (feedback) setMutationStatus(null);
      Alert.alert("No pudimos guardar el cambio", userFacingError(nextError));
      throw nextError;
    }
  }, [apiRequest, load]);

  async function togglePinnedMealCompletion(targetMealKey: string, completed: boolean) {
    if (!todayContext || savingMealKey) return;
    const previous = todayContext;
    setSavingMealKey(targetMealKey);
    setCompletionError(null);
    const mealExecution = normalizeMealExecution(todayContext.meal_execution);
    setTodayContext({
      ...todayContext,
      meal_execution: mealExecution.map((entry) => entry.meal_key === targetMealKey ? { ...entry, status: completed ? "completed" : "skipped" } : entry),
    });
    try {
      const payload: MealCheckInInput = { action: completed ? "completed" : "skipped", idempotency_key: Crypto.randomUUID() };
      setTodayContext(await apiRequest<TodayData>(`/api/v1/today/pinned-plan/meals/${encodeURIComponent(targetMealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" }));
    } catch (nextError) {
      setTodayContext(previous);
      setCompletionError({ mealKey: targetMealKey, message: userFacingError(nextError) });
    } finally {
      setSavingMealKey(null);
    }
  }

  async function togglePinnedPreparedFood(targetMealKey: string, foodKey: string) {
    if (!todayContext) return;
    const previous = todayContext;
    const mealExecution = normalizeMealExecution(todayContext.meal_execution);
    const execution = mealExecution.find((entry) => entry.meal_key === targetMealKey);
    const prepared = execution?.prepared_food_keys.includes(foodKey) ?? false;
    setTodayContext({
      ...todayContext,
      meal_execution: mealExecution.map((entry) => entry.meal_key !== targetMealKey ? entry : {
        ...entry,
        prepared_food_keys: prepared ? entry.prepared_food_keys.filter((key) => key !== foodKey) : [...entry.prepared_food_keys, foodKey],
      }),
    });
    try {
      const payload: MealCheckInInput = { action: prepared ? "food_unprepared" : "food_prepared", food_snapshot_key: foodKey, idempotency_key: Crypto.randomUUID() };
      setTodayContext(await apiRequest<TodayData>(`/api/v1/today/pinned-plan/meals/${encodeURIComponent(targetMealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" }));
    } catch (nextError) {
      setTodayContext(previous);
      setError(userFacingError(nextError));
    }
  }

  async function togglePinnedMealDetailFood(foodKey: string) {
    if (!mealKey) return;
    const prepared = pinnedMealExecution ? normalizeMealExecutionItem(pinnedMealExecution).prepared_food_keys.includes(foodKey) : false;
    const previous = pinnedMealExecution;
    setPinnedMealExecution((current) => ({
      meal_key: mealKey,
      status: current?.status ?? "planned",
      last_event_id: current?.last_event_id ?? null,
      recorded_at: current?.recorded_at ?? null,
      note: current?.note ?? "",
      prepared_food_keys: prepared ? (current?.prepared_food_keys ?? []).filter((key) => key !== foodKey) : [...(current?.prepared_food_keys ?? []), foodKey],
    }));
    try {
      const payload: MealCheckInInput = { action: prepared ? "food_unprepared" : "food_prepared", food_snapshot_key: foodKey, idempotency_key: Crypto.randomUUID() };
      const updated = await apiRequest<TodayData>(`/api/v1/today/pinned-plan/meals/${encodeURIComponent(mealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" });
      setPinnedMealExecution(normalizeMealExecution(updated.meal_execution).find((entry) => entry.meal_key === mealKey) ?? null);
    } catch (nextError) {
      setPinnedMealExecution(previous);
      setError(userFacingError(nextError));
    }
  }
  const loadLabelImage = useCallback(async () => {
    if (!item?.label_capture_receipt_id) return;
    setLabelImageBusy(true);
    try {
      setLabelImage(await apiRequest<FoodLabelImage>(`/api/v1/foods/label-captures/${item.label_capture_receipt_id}/image`));
    } catch (nextError) {
      Alert.alert("No pudimos abrir la etiqueta", userFacingError(nextError));
    } finally {
      setLabelImageBusy(false);
    }
  }, [apiRequest, item]);
  const deleteLabelImage = useCallback(() => {
    if (!item?.label_capture_receipt_id) return;
    Alert.alert("Eliminar copia de la etiqueta", "El alimento se conservará, pero esta imagen no podrá recuperarse.", [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => { void (async () => {
        setLabelImageBusy(true);
        try {
          await apiRequest(`/api/v1/foods/label-captures/${item.label_capture_receipt_id}/image`, { method: "DELETE" });
          setLabelImage(null);
          setItem((current) => current ? { ...current, label_image_available: false } : current);
        } catch (nextError) {
          Alert.alert("No pudimos eliminar la imagen", userFacingError(nextError));
        } finally {
          setLabelImageBusy(false);
        }
      })(); } },
    ]);
  }, [apiRequest, item]);
  useFocusEffect(useCallback(() => { if (status === "authenticated" && id) void load(); }, [id, load, status]));
  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !item) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!item) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;
  const actionsModal = <LibraryActions apiRequest={apiRequest} entitySlug={entitySlug} initialAction={actionSheet === "change-time" ? "change-time" : undefined} item={item} key={actionSheet ?? "closed"} mealTimeChange={hasMealTimeContext ? {
    initialTime: contextTime,
    onSubmit: async (hour: string) => {
      await apiRequest<CompositionMutationResult>(`/api/v1/library/daily-plans/${contextDailyPlanId}/meals/${contextDailyPlanMealId}`, {
        body: JSON.stringify({ hour }),
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      });
      setContextTime(hour);
    },
  } : undefined} mealTimeInMenu={false} onCompleted={handleActionCompleted} onVisibleChange={(visible) => { if (!visible) setActionSheet(null); }} renderTrigger={() => null} visible={actionSheet != null} />;
  const mutationStatusModal = <MutationStatusModal onFinished={() => setMutationStatus(null)} status={mutationStatus} />;
  if (item.entity === "program") {
    return <><ProgramDetailPreview
      footer={<>{item.can_calendarize && !item.is_draft ? <Button bleed label="Calendarizar este programa" onPress={() => router.push(`/program/activate?programId=${item.id}` as Href)} /> : null}<EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /></>}
      item={item}
      onAddWeek={item.can_calendarize ? () => router.push(`/pickers/week-to-program?programId=${item.id}` as Href) : undefined}
      onAssignDailyPlan={item.can_calendarize ? (week, day) => router.push(pickerHref("dailyplan-to-program", { programId: item.id, weekNumber: week, dayNumber: day })) : undefined}
      onDuplicateWeek={item.can_calendarize ? async (week) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}/duplicate`, { method: "POST" }); } : undefined}
      onRemoveDailyPlan={item.can_calendarize ? async (week, day) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}/days/${day}`, { method: "DELETE" }); } : undefined}
      onRemoveWeek={item.can_calendarize ? async (week) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}`, { method: "DELETE" }); } : undefined}
      onReorderDailyPlans={item.can_calendarize ? async (week, orderedDays) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/${week}/days/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: orderedDays }) }, { loadingLabel: "Actualizando programa", successLabel: "Programa actualizado" }); } : undefined}
      onReorderWeeks={item.can_calendarize ? async (weeks) => { await mutateComposition(`/api/v1/library/programs/${item.id}/weeks/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: weeks }) }, { loadingLabel: "Actualizando programa", successLabel: "Programa actualizado" }); } : undefined}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollable
    />{actionsModal}{mutationStatusModal}</>;
  }
  const panelCount = item.panel.kind === "foods" ? item.panel.foods.length : item.panel.kind === "meals" ? item.panel.meals.length : item.panel.kind === "weeks" ? item.panel.weeks.length : 0;
  const isEmptyDraft = item.is_draft && panelCount === 0 && (item.entity === "meal" || item.entity === "dailyPlan");
  const contextualDayId = Number(calendarizedDayId);
  const foodItems = item.panel.foods.map(foodPanelItem);
  const openFood = (food: FoodPanelItem) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); };
  const mealExecution = normalizeMealExecution(todayContext?.meal_execution);
  const normalizedPinnedMealExecution = pinnedMealExecution ? normalizeMealExecutionItem(pinnedMealExecution) : null;
  const completedPinnedMealKeys = new Set(mealExecution.filter((entry) => entry.status === "completed").map((entry) => entry.meal_key));
  const mealItems = item.panel.meals.map((meal) => ({ ...mealPanelItem(meal), completed: isPinnedPlan && completedPinnedMealKeys.has(meal.id) }));
  const foodEditing = item.entity === "meal" ? {
    onDelete: async (food: FoodPanelItem) => { if (food.relationId) await mutateComposition(`/api/v1/library/meals/${item.id}/foods/${food.relationId}`, { method: "DELETE" }); },
    onEditPortion: (food: FoodPanelItem) => { if (food.relationId && food.detailId) router.push(pickerConfigureHref("food-to-meal", { contextDailyPlanId: hasMealTimeContext ? contextDailyPlanId : undefined, contextDailyPlanMealId: hasMealTimeContext ? contextDailyPlanMealId : undefined, relationId: food.relationId, returnTo: isContextualMealCreation ? currentDetailHref : undefined, selectedId: food.detailId, targetId: item.id, weekNumber: 1 })); },
    onReorder: async (foods: FoodPanelItem[]) => { await mutateComposition(`/api/v1/library/meals/${item.id}/foods/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: foods.map((food) => food.relationId) }) }, { loadingLabel: "Actualizando comida", successLabel: "Comida actualizada" }); },
    onReplace: (food: FoodPanelItem) => { if (food.relationId) router.push(pickerHref("food-to-meal", { mealFoodId: food.relationId, mealId: item.id, ...(hasMealTimeContext ? { dailyPlanId: contextDailyPlanId, dailyPlanMealId: contextDailyPlanMealId } : {}), ...(isContextualMealCreation ? { returnTo: String(currentDetailHref) } : {}) })); },
  } : undefined;
  const mealEditing = item.entity === "dailyPlan" ? {
    onChangeTime: (meal: MealPanelItem) => { if (meal.relationId) setPanelTimeMeal(meal); },
    onDelete: async (meal: MealPanelItem) => { if (meal.relationId) await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/${meal.relationId}`, { method: "DELETE" }); },
    onOpen: (meal: MealPanelItem) => { if (meal.detailId && meal.relationId) router.push({ pathname: "/libraries/meals/[id]", params: { dailyPlanId: String(item.id), dailyPlanMealId: String(meal.relationId), id: String(meal.detailId), mealTime: meal.time ?? "", ...(isPinnedPlan ? { pinned: "1", mealKey: meal.id } : {}) } } as Href); },
    onReorder: async (meals: MealPanelItem[]) => { await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/order`, { method: "PUT", body: JSON.stringify({ ordered_ids: meals.map((meal) => meal.relationId) }) }, { loadingLabel: "Actualizando plan", successLabel: "Plan actualizado" }); },
    onReplace: (meal: MealPanelItem) => { if (meal.relationId) router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id, dailyPlanMealId: meal.relationId })); },
  } : undefined;
  const detailIndicators = isEmptyDraft ? undefined : [
    ...item.indicators,
    ...(item.entity === "meal" && hasMealTimeContext && contextTime
      ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: contextTime }]
      : []),
  ];
  return <><NestableScrollContainer contentContainerStyle={styles.content} onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }} scrollEventThrottle={16} style={styles.screen}><EntityDetailPage
    beforeNutrition={isPinnedPlan && item.panel.meals.length ? <DailyMealCompletionCard mealExecution={mealExecution} mealKeys={item.panel.meals.map((meal) => meal.id)} /> : isPinnedMealContext ? <MealCompletionCard controller={pinnedMealAdherence} /> : undefined}
    completion={isPinnedPlan ? { noteCount: mealExecution.filter((entry) => entry.note.trim()).length } : isPinnedMealContext ? { noteCount: normalizedPinnedMealExecution?.note.trim() ? 1 : 0 } : undefined}
    entity={item.entity}
    indicators={detailIndicators}
    nutrition={libraryNutrition(item.nutrition)}
    showNutrition={!isEmptyDraft}
    subtitle={item.subtitle || undefined}
    title={item.name}>
    {item.entity === "food" && item.label_image_available ? <><SectionDivider /><EntityDetailSection title="Etiqueta guardada">
      {labelImage ? <Image resizeMode="contain" source={{ uri: `data:${labelImage.content_type};base64,${labelImage.image_base64}` }} style={styles.labelImage} /> : null}
      {!labelImage ? <Button label="Ver copia procesada" loading={labelImageBusy} onPress={() => void loadLabelImage()} variant="secondary" /> : null}
      <Button label="Eliminar copia" loading={labelImageBusy} onPress={deleteLabelImage} variant="secondary" />
    </EntityDetailSection></> : null}
    {!isEmptyDraft && item.panel.kind !== "none" ? <EntityDetailSection detail={item.panel.kind === "weeks" ? `${panelCount} elementos` : undefined} title={sectionTitles[item.panel.kind]}>{item.panel.kind === "foods" ? <FoodPanels editing={foodEditing} items={foodItems} nestedScroll onOpenItem={openFood} preparation={isPinnedMealContext && pinnedMealAdherence.available ? { isPrepared: (food) => normalizedPinnedMealExecution?.prepared_food_keys.includes(food.id) ?? false, onToggle: (food) => void togglePinnedMealDetailFood(food.id) } : undefined} /> : null}{item.panel.kind === "meals" ? <MealPanels editing={mealEditing} items={mealItems} nestedScroll onOpenItem={mealEditing?.onOpen} /> : null}{item.panel.kind === "weeks" ? <ProgramPanels items={item.panel.weeks} /> : null}</EntityDetailSection> : null}
    {item.entity === "meal" ? <Button bleed label="+ Agregar alimento" onPress={() => router.push(pickerHref("food-to-meal", { mealId: item.id, ...(hasMealTimeContext ? { dailyPlanId: contextDailyPlanId, dailyPlanMealId: contextDailyPlanMealId } : {}), ...(isContextualMealCreation ? { returnTo: String(currentDetailHref) } : {}) }))} /> : null}
    {item.entity === "meal" && foodItems.length > 0 ? <><SectionDivider /><EntityDetailSection detail={`${foodItems.length} alimentos`} title="Detalle de cada Alimento"><FoodDetailCardList items={foodItems} onOpenFood={openFood} /></EntityDetailSection></> : null}
    {item.entity === "dailyPlan" ? <Button bleed label="+ Agregar Comida" onPress={() => router.push(pickerHref("meal-to-dailyplan", { dailyPlanId: item.id }))} /> : null}
    {item.entity === "meal" && isPinnedMealContext ? <MealNoteCard controller={pinnedMealAdherence} /> : null}
    {item.entity === "meal" && !isPinnedMealContext && Number.isInteger(contextualDayId) && contextualDayId > 0 && mealKey ? <MealAdherenceCheckIn dayId={contextualDayId} mealKey={mealKey} /> : null}
    {item.entity === "dailyPlan" && item.panel.kind === "meals" && item.panel.meals.length > 0 ? <><SectionDivider /><EntityDetailSection detail={`${item.panel.meals.length} comidas`} title="Detalle de cada Comida"><DailyPlanMealCards dailyPlanId={item.id} items={item.panel.meals} onRemove={async (meal) => { if (meal.relation_id) await mutateComposition(`/api/v1/library/daily-plans/${item.id}/meals/${meal.relation_id}`, { method: "DELETE" }); }} pinnedTracking={isPinnedPlan ? { completionError, mealExecution, onToggleCompleted: (targetMealKey, completed) => void togglePinnedMealCompletion(targetMealKey, completed), onTogglePrepared: (targetMealKey, foodKey) => void togglePinnedPreparedFood(targetMealKey, foodKey), savingMealKey } : undefined} /></EntityDetailSection></> : null}
    {item.entity === "dailyPlan" && item.panel.foods.length > 0 ? <><SectionDivider /><EntityDetailSection detail={`${item.panel.foods.length} alimentos`} title="Alimentos en este plan diario"><FoodPanels items={item.panel.foods.map(foodPanelItem)} onOpenItem={openFood} /></EntityDetailSection></> : null}
    {item.entity === "dailyPlan" && todayContext?.calendarization == null ? <Button bleed label={isPinnedPlan ? "Dejar de fijar como Plan de hoy" : "Fijar como Plan de hoy"} onPress={() => confirmPinnedPlan(!isPinnedPlan)} variant={isPinnedPlan ? "secondary" : "primary"} /> : null}
    {!isEmptyDraft ? <EntityDetailMetadata creator={item.creator} updatedAt={libraryDate(item.created_at)} /> : null}
  </EntityDetailPage></NestableScrollContainer>{actionsModal}{mutationStatusModal}<CalendarizedEntityActions
    entityName={panelTimeMeal?.name ?? "Comida"}
    initialAction="change-time"
    key={panelTimeMeal?.id ?? "closed-panel-time-change"}
    onVisibleChange={(visible) => { if (!visible) setPanelTimeMeal(null); }}
    timeChange={panelTimeMeal?.relationId ? {
      initialTime: panelTimeMeal.time,
      onSubmit: async (hour) => {
        await apiRequest<CompositionMutationResult>(`/api/v1/library/daily-plans/${item.id}/meals/${panelTimeMeal.relationId}`, {
          body: JSON.stringify({ hour }),
          headers: { "Content-Type": "application/json" },
          method: "PATCH",
        });
        await load();
      },
    } : undefined}
    timeChangeInMenu={false}
    visible={panelTimeMeal != null}
  /></>;
}
const styles = StyleSheet.create({ screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 }, content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg }, loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen }, labelImage: { backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 320, width: "100%" } });
