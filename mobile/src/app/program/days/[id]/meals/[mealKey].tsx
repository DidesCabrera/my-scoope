import { Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealExecutionItem, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { MealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { snapshotAllocation, snapshotCalories, snapshotFoodPanelItems } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels } from "@/components/panels";
import { Button, InlineNotice, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

export default function CalendarizedMealDetailScreen() {
  const { id, mealKey } = useLocalSearchParams<{ id: string; mealKey: string }>();
  const { status, apiRequest } = useSession();
  const [meal, setMeal] = useState<MealSnapshot | null>(null);
  const [execution, setExecution] = useState<MealExecutionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const setHeaderPresentation = useHeaderPresentation();
  const dayId = Number(id);

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
      action: meal ? { label: `Más acciones para ${meal.name ?? "esta comida"}`, onPress: () => setActionsVisible(true) } : undefined,
      entity: "meal",
      identityVisible: compactHeaderVisible,
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
          carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
          fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
          protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
        }}
        title={meal.name ?? "Comida"}>
        <EntityDetailSection detail={`${foods.length} alimentos`} title="Tabla de comparación entre alimentos">
          <FoodPanels items={foods} />
        </EntityDetailSection>
        <MealAdherenceCheckIn dayId={dayId} mealKey={mealKey} onChange={setExecution} />
      </EntityDetailPage>
    </ScrollView>
    <CalendarizedEntityActions
      entityName={meal.name ?? "Comida"}
      onVisibleChange={setActionsVisible}
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
      visible={actionsVisible}
    />
    </>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
