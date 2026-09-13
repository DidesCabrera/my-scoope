import { Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealCheckInInput, MealExecutionItem, MealSnapshot, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { MealCompletionCard, MealNoteCard, useMealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { snapshotCalories, snapshotFoodPanelItems, snapshotMacroDistribution } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection, FoodDetailCardList } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { pickerHref } from "@/components/pickers/composition-picker-screen";
import { Button, InlineNotice, SectionDivider, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

export default function CalendarizedMealDetailScreen() {
  const { id, mealKey } = useLocalSearchParams<{ id: string; mealKey: string }>();
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [meal, setMeal] = useState<MealSnapshot | null>(null);
  const [execution, setExecution] = useState<MealExecutionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionSheet, setActionSheet] = useState<"change-time" | "menu" | null>(null);
  const setHeaderPresentation = useHeaderPresentation();
  const dayId = Number(id);
  const adherence = useMealAdherenceCheckIn({ dayId, mealKey, onChange: setExecution });

  async function togglePreparedFood(foodKey: string) {
    const prepared = execution?.prepared_food_keys.includes(foodKey) ?? false;
    const previous = execution;
    setExecution((current) => ({
      meal_key: mealKey,
      status: current?.status ?? "planned",
      last_event_id: current?.last_event_id ?? null,
      recorded_at: current?.recorded_at ?? null,
      note: current?.note ?? "",
      prepared_food_keys: prepared
        ? (current?.prepared_food_keys ?? []).filter((key) => key !== foodKey)
        : [...(current?.prepared_food_keys ?? []), foodKey],
    }));
    try {
      const payload: MealCheckInInput = {
        action: prepared ? "food_unprepared" : "food_prepared",
        food_snapshot_key: foodKey,
        idempotency_key: Crypto.randomUUID(),
      };
      const updated = await apiRequest<TodayData>(`/api/v1/days/${dayId}/meals/${encodeURIComponent(mealKey)}/check-ins`, { body: JSON.stringify(payload), method: "POST" });
      setExecution(updated.meal_execution.find((item) => item.meal_key === mealKey) ?? null);
    } catch (nextError) {
      setExecution(previous);
      setError(userFacingError(nextError));
    }
  }

  function applyDay(day: CalendarizedDayDetail) {
    setMeal(day.plan_snapshot?.meals?.find((item) => item.key === mealKey) ?? null);
    setExecution(day.meal_execution.find((item) => item.meal_key === mealKey) ?? null);
  }

  async function mutateFoods(path: string, init: { body?: string; method: "DELETE" | "PATCH" | "PUT" }) {
    try {
      applyDay(await apiRequest<CalendarizedDayDetail>(path, init));
    } catch (nextError) {
      setError(userFacingError(nextError));
      throw nextError;
    }
  }

  const load = useCallback(async () => {
    if (!Number.isInteger(dayId) || dayId <= 0 || !mealKey) return;
    setLoading(true);
    setError(null);
    try {
      const day = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${dayId}`);
      const match = day.plan_snapshot?.meals?.find((item) => item.key === mealKey) ?? null;
      setMeal(match);
      setExecution(day.meal_execution.find((item) => item.meal_key === mealKey) ?? null);
      if (!match) setError("Esta comida ya no está disponible en el día calendarizado.");
    } catch (nextError) {
      setError(userFacingError(nextError));
      setMeal(null);
      setExecution(null);
    } finally {
      setLoading(false);
    }
  }, [apiRequest, dayId, mealKey]);

  useFocusEffect(useCallback(() => {
    if (status === "authenticated") void load();
  }, [load, status]));

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      mode: "library-detail",
      action: meal ? { label: `Más acciones para ${meal.name ?? "esta comida"}`, onPress: () => setActionSheet("menu") } : undefined,
      entity: "meal",
      identityVisible: compactHeaderVisible,
      secondaryAction: meal ? { icon: "clock", label: "Cambiar hora", onPress: () => setActionSheet("change-time") } : undefined,
      title: meal?.name ?? "Comida del programa",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, meal, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !meal) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!meal) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;

  const totals = meal.totals;
  const foods = snapshotFoodPanelItems(meal);
  return (
    <>
    <ScrollView
      contentContainerStyle={styles.content}
      onScroll={({ nativeEvent }) => {
        const visible = nativeEvent.contentOffset.y > 1;
        if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible);
      }}
      scrollEventThrottle={16}
      style={styles.screen}>
      <EntityDetailPage
        entity="meal"
        beforeNutrition={<MealCompletionCard controller={adherence} />}
        completion={{
          completedCount: execution?.status === "completed" ? 1 : 0,
          noteCount: execution?.note.trim() ? 1 : 0,
        }}
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
        title={meal.name ?? "Comida"}>
        <EntityDetailSection title="Tabla de comparación entre alimentos">
          <FoodPanels
            editing={{
              onDelete: async (food) => mutateFoods(`/api/v1/program/days/${dayId}/meals/${encodeURIComponent(mealKey)}/foods/${encodeURIComponent(food.id)}`, { method: "DELETE" }),
              onReorder: async (items: FoodPanelItem[]) => mutateFoods(`/api/v1/program/days/${dayId}/meals/${encodeURIComponent(mealKey)}/foods/order`, { body: JSON.stringify({ ordered_keys: items.map((item) => item.id) }), method: "PUT" }),
              onReplace: (food) => router.push(pickerHref("food-to-calendarized-meal", { dayId, mealKey, relationKey: food.id })),
              onUpdateQuantity: async (food, quantity) => mutateFoods(`/api/v1/program/days/${dayId}/meals/${encodeURIComponent(mealKey)}/foods/${encodeURIComponent(food.id)}`, { body: JSON.stringify({ quantity }), method: "PATCH" }),
            }}
            items={foods}
            preparation={adherence.available ? {
              isPrepared: (food) => execution?.prepared_food_keys.includes(food.id) ?? false,
              onToggle: (food) => void togglePreparedFood(food.id),
            } : undefined}
          />
        </EntityDetailSection>
        <Button
          bleed
          label="+ Agregar alimento"
          onPress={() => router.push(pickerHref("food-to-calendarized-meal", { dayId, mealKey }))}
        />
        {foods.length ? <><SectionDivider /><EntityDetailSection detail={`${foods.length} alimentos`} title="Detalle de cada Alimento"><FoodDetailCardList items={foods} /></EntityDetailSection></> : null}
        <MealNoteCard controller={adherence} />
      </EntityDetailPage>
    </ScrollView>
    <CalendarizedEntityActions
      entityName={meal.name ?? "Comida"}
      initialAction={actionSheet === "change-time" ? "change-time" : undefined}
      key={actionSheet ?? "closed"}
      onVisibleChange={(visible) => { if (!visible) setActionSheet(null); }}
      rename={{
        onSubmit: async (name) => {
          const day = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${dayId}/meals/${encodeURIComponent(mealKey)}/name`, {
            body: JSON.stringify({ name }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          const updatedMeal = day.plan_snapshot?.meals?.find((item) => item.key === mealKey) ?? null;
          setMeal(updatedMeal);
          setExecution(day.meal_execution.find((item) => item.meal_key === mealKey) ?? null);
        },
      }}
      timeChange={{
        initialTime: meal.hour,
        onSubmit: async (hour) => {
          const day = await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${dayId}/meals/${encodeURIComponent(mealKey)}`, {
            body: JSON.stringify({ hour }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          const updatedMeal = day.plan_snapshot?.meals?.find((item) => item.key === mealKey) ?? null;
          setMeal(updatedMeal);
          setExecution(day.meal_execution.find((item) => item.meal_key === mealKey) ?? null);
          await refreshNativeReminders(apiRequest);
        },
      }}
      timeChangeInMenu={false}
      visible={actionSheet != null}
    />
    </>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
