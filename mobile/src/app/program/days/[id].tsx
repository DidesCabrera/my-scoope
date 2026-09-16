import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { NestableScrollContainer } from "react-native-draggable-flatlist";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealCheckInInput, MealExecutionItem, MealSnapshot, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { MealCompletionToggleCard } from "@/components/calendarization/meal-adherence-check-in";
import { DailyMealCompletionCard } from "@/components/calendarization/meal-completion-summary";
import { normalizeMealExecution } from "@/components/calendarization/meal-execution";
import { snapshotCalories, snapshotDailyPlanFoodPanelItems, snapshotFoodPanelItems, snapshotMacroDistribution, snapshotMealPanelItem } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { isHeaderIdentityVisible } from "@/components/navigation/header-scroll";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels, type MealPanelItem } from "@/components/panels";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { Button, ContentPanel, EntityCardAction, InlineNotice, MutationStatusModal, SectionDivider, textStyles, useMutationStatus } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function completionFor(items: MealExecutionItem[]) {
  const normalized = normalizeMealExecution(items);
  return {
    noteCount: normalized.filter((item) => item.note.trim()).length,
  };
}

function CalendarizedMealCards({ completionError, dayId, mealExecution, meals, onToggleCompleted, onTogglePrepared, savingMealKey }: { completionError: { mealKey: string; message: string } | null; dayId: number; mealExecution: MealExecutionItem[]; meals: MealSnapshot[]; onToggleCompleted(mealKey: string, completed: boolean): void; onTogglePrepared(mealKey: string, foodKey: string): void; savingMealKey: string | null }) {
  const router = useRouter();
  const normalizedMealExecution = normalizeMealExecution(mealExecution);
  return (
    <View style={styles.mealCardList}>
      {meals.map((meal, index) => {
        const totals = meal.totals;
        const foods = snapshotFoodPanelItems(meal);
        const execution = normalizedMealExecution.find((item) => item.meal_key === meal.key);
        return (
          <View key={meal.key ?? `${meal.name}-${index}`}>
            <NutritionEntityCard
              actions={meal.key ? (
                <EntityCardAction
                  label={`Ver detalle de ${meal.name ?? "la comida"}`}
                  onPress={() => router.push({
                    pathname: "/program/days/[id]/meals/[mealKey]",
                    params: { id: String(dayId), mealKey: meal.key ?? "" },
                  } as Href)}
                  role="link">
                  <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                </EntityCardAction>
              ) : null}
              completion={{ noteCount: execution?.note.trim() ? 1 : 0 }}
              entity="meal"
              eyebrow={`Comida ${index + 1}`}
              indicators={[
                { icon: "food", label: "alimentos", value: foods.length },
                ...(meal.hour ? [{ icon: "clock" as const, iconPosition: "leading" as const, label: "hora", tone: "surfaceCard" as const, value: meal.hour.slice(0, 5) }] : []),
              ]}
              nutrition={{
                calories: snapshotCalories(totals),
                carbs: { allocation: snapshotMacroDistribution(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
                fat: { allocation: snapshotMacroDistribution(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
                protein: { allocation: snapshotMacroDistribution(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
              }}
              beforeNutrition={meal.key ? <MealCompletionToggleCard completed={execution?.status === "completed"} error={completionError?.mealKey === meal.key ? completionError.message : null} onToggle={(completed) => onToggleCompleted(meal.key ?? "", completed)} saving={savingMealKey != null} /> : null}
              title={meal.name ?? "Comida"}>
              <FoodPanels items={foods} onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }} preparation={meal.key ? {
                disabled: savingMealKey != null,
                isPrepared: (food) => execution?.prepared_food_keys.includes(food.id) ?? false,
                onToggle: (food) => onTogglePrepared(meal.key ?? "", food.id),
              } : undefined} />
            </NutritionEntityCard>
          </View>
        );
      })}
    </View>
  );
}

export default function ProgramDayScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [day, setDay] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const [timeChangeMeal, setTimeChangeMeal] = useState<MealPanelItem | null>(null);
  const [savingMealKey, setSavingMealKey] = useState<string | null>(null);
  const [completionError, setCompletionError] = useState<{ mealKey: string; message: string } | null>(null);
  const { clearStatus, runWithStatus, status: mutationStatus } = useMutationStatus();
  const setHeaderPresentation = useHeaderPresentation();

  async function toggleMealCompletion(mealKey: string, completed: boolean) {
    if (!day || savingMealKey) return;
    const previous = day;
    setSavingMealKey(mealKey);
    setCompletionError(null);
    const mealExecution = normalizeMealExecution(day.meal_execution);
    setDay({
      ...day,
      meal_execution: mealExecution.map((item) => item.meal_key === mealKey ? {
        ...item,
        status: completed ? "completed" : "skipped",
      } : item),
    });
    try {
      const payload: MealCheckInInput = { action: completed ? "completed" : "skipped", idempotency_key: Crypto.randomUUID() };
      const updatedToday = await apiRequest<TodayData>(`/api/v1/days/${day.id}/meals/${encodeURIComponent(mealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" });
      const updated = updatedToday.day_id === day.id
        ? { ...day, meal_execution: normalizeMealExecution(updatedToday.meal_execution) }
        : await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${day.id}`);
      setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
    } catch (nextError) {
      setDay(previous);
      setCompletionError({ mealKey, message: userFacingError(nextError) });
    } finally {
      setSavingMealKey(null);
    }
  }

  async function togglePreparedFood(mealKey: string, foodKey: string) {
    if (!day || savingMealKey) return;
    const previous = day;
    setSavingMealKey(mealKey);
    const mealExecution = normalizeMealExecution(day.meal_execution);
    const execution = mealExecution.find((item) => item.meal_key === mealKey);
    const prepared = execution?.prepared_food_keys.includes(foodKey) ?? false;
    setDay({
      ...day,
      meal_execution: mealExecution.map((item) => item.meal_key !== mealKey ? item : {
        ...item,
        prepared_food_keys: prepared ? item.prepared_food_keys.filter((key) => key !== foodKey) : [...item.prepared_food_keys, foodKey],
      }),
    });
    try {
      const payload: MealCheckInInput = { action: prepared ? "food_unprepared" : "food_prepared", food_snapshot_key: foodKey, idempotency_key: Crypto.randomUUID() };
      const updatedToday = await apiRequest<TodayData>(`/api/v1/days/${day.id}/meals/${encodeURIComponent(mealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" });
      const updated = updatedToday.day_id === day.id
        ? { ...day, meal_execution: normalizeMealExecution(updatedToday.meal_execution) }
        : await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${day.id}`);
      setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
    } catch (nextError) {
      setDay(previous);
      setError(userFacingError(nextError));
    } finally {
      setSavingMealKey(null);
    }
  }

  async function mutateMeals(path: string, init: { body?: string; method: "DELETE" | "PUT" }) {
    try {
      const updated = await apiRequest<CalendarizedDayDetail>(path, init);
      setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${id}`);
      setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, id]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      mode: "library-detail",
      action: day?.has_plan ? { label: `Más acciones para ${day.plan_snapshot?.name ?? day.plan_name ?? "este plan"}`, onPress: () => setActionsVisible(true) } : undefined,
      entity: "dailyPlan",
      identityVisible: compactHeaderVisible,
      title: day?.plan_snapshot?.name ?? day?.plan_name ?? "Detalle del día",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, day, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !day) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Abriendo el día…</Text></View>;
  if (!day) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;

  const snapshot = day.plan_snapshot;
  const meals = snapshot?.meals ?? [];
  const totals = snapshot?.totals;
  const totalCalories = snapshotCalories(totals);
  const mealExecution = normalizeMealExecution(day.meal_execution);
  const completedMealKeys = new Set(mealExecution.filter((item) => item.status === "completed").map((item) => item.meal_key));
  const mealItems = meals.map((meal, index) => ({
    ...snapshotMealPanelItem(meal, index, totals),
    completed: Boolean(meal.key && completedMealKeys.has(meal.key)),
  }));
  const foods = snapshotDailyPlanFoodPanelItems(meals);
  const openMeal = (meal: MealPanelItem) => router.push({
    pathname: "/program/days/[id]/meals/[mealKey]",
    params: { id: String(day.id), mealKey: meal.id },
  } as Href);

  return (
    <>
    <NestableScrollContainer
      contentContainerStyle={styles.content}
      onScroll={({ nativeEvent }) => setCompactHeaderVisible(isHeaderIdentityVisible(nativeEvent.contentOffset.y))}
      scrollEventThrottle={16}
      showsVerticalScrollIndicator={false}
      style={styles.screen}>
      {day.has_plan && snapshot ? (
        <EntityDetailPage
          entity="dailyPlan"
          beforeNutrition={<DailyMealCompletionCard mealExecution={day.meal_execution} mealKeys={meals.map((meal) => meal.key)} />}
          completion={completionFor(mealExecution)}
          indicators={[
            { icon: "day", label: "posición", value: `S${day.week_number} · D${day.day_number}` },
            { icon: "meal", label: "comidas", value: meals.length },
            { icon: "day", iconPosition: "leading", label: "fecha", tone: "surfaceMuted", value: displayDate(day.calendar_date) },
          ]}
          nutrition={{
            calories: totalCalories,
            carbs: { allocation: snapshotMacroDistribution(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
            fat: { allocation: snapshotMacroDistribution(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
            protein: { allocation: snapshotMacroDistribution(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
          }}
          title={snapshot.name ?? day.plan_name ?? "Plan diario"}>
          <EntityDetailSection title="Tabla de comparación entre comidas">
            <MealPanels
              editing={{
                onChangeTime: setTimeChangeMeal,
                onDelete: async (meal) => mutateMeals(`/api/v1/program/days/${day.id}/meals/${encodeURIComponent(meal.id)}`, { method: "DELETE" }),
                onOpen: openMeal,
                onReorder: async (items: MealPanelItem[]) => runWithStatus(
                  () => mutateMeals(`/api/v1/program/days/${day.id}/meals/order`, { body: JSON.stringify({ ordered_keys: items.map((item) => item.id) }), method: "PUT" }),
                  { loadingLabel: "Actualizando plan", successLabel: "Plan actualizado" },
                ),
                onReplace: (meal) => router.push(pickerHref("meal-to-calendarized-day", { dayId: day.id, relationKey: meal.id })),
              }}
              items={mealItems}
              nestedScroll
              onOpenItem={openMeal}
            />
          </EntityDetailSection>
          <Button
            bleed
            label="+ Agregar Comida"
            onPress={() => router.push(pickerHref("meal-to-calendarized-day", { dayId: day.id }))}
          />
          {meals.length ? (
            <>
              <SectionDivider />
              <EntityDetailSection detail={`${meals.length} comidas`} title="Detalle de cada Comida">
                <CalendarizedMealCards completionError={completionError} dayId={day.id} mealExecution={mealExecution} meals={meals} onToggleCompleted={(mealKey, completed) => void toggleMealCompletion(mealKey, completed)} onTogglePrepared={(mealKey, foodKey) => void togglePreparedFood(mealKey, foodKey)} savingMealKey={savingMealKey} />
              </EntityDetailSection>
            </>
          ) : null}
          {foods.length ? (
            <>
              <SectionDivider />
              <EntityDetailSection detail={`${foods.length} alimentos`} title="Alimentos en este plan diario">
                <FoodPanels items={foods} onOpenItem={(food) => { if (food.detailId != null) router.push(`/libraries/foods/${food.detailId}` as Href); }} />
              </EntityDetailSection>
            </>
          ) : null}
          <ContentPanel muted title="Información del día">
            <View style={styles.metadataRow}><Text style={styles.metadataLabel}>Fecha</Text><Text style={styles.metadataValue}>{displayDate(day.calendar_date)}</Text></View>
            <View style={styles.metadataRow}><Text style={styles.metadataLabel}>Ubicación</Text><Text style={styles.metadataValue}>Semana {day.week_number} · Día {day.day_number}</Text></View>
          </ContentPanel>
        </EntityDetailPage>
      ) : (
        <ContentPanel muted title="Día sin plan">
          <Text style={textStyles.muted}>La calendarización conserva esta fecha, pero el programa no tiene un plan nutricional asignado.</Text>
        </ContentPanel>
      )}
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    </NestableScrollContainer>
    <CalendarizedEntityActions
      entityName={snapshot?.name ?? day.plan_name ?? "Plan diario"}
      onVisibleChange={setActionsVisible}
      rename={{
        onSubmit: async (name) => {
          const updated = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${day.id}`, {
            body: JSON.stringify({ name }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
        },
      }}
      visible={actionsVisible}
    />
    <CalendarizedEntityActions
      entityName={timeChangeMeal?.name ?? "Comida"}
      initialAction="change-time"
      key={timeChangeMeal?.id ?? "closed-time-change"}
      onVisibleChange={(visible) => { if (!visible) setTimeChangeMeal(null); }}
      timeChange={timeChangeMeal ? {
        initialTime: timeChangeMeal.time,
        onSubmit: async (hour) => {
          const updated = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${day.id}/meals/${encodeURIComponent(timeChangeMeal.id)}`, {
            body: JSON.stringify({ hour }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          setDay({ ...updated, meal_execution: normalizeMealExecution(updated.meal_execution) });
          await refreshNativeReminders(apiRequest);
        },
      } : undefined}
      timeChangeInMenu={false}
      visible={timeChangeMeal != null}
    />
    <MutationStatusModal onFinished={clearStatus} status={mutationStatus} />
    </>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  mealCardList: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  metadataLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  metadataRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  metadataValue: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: "500", textAlign: "right", textTransform: "capitalize" },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
