import { Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MacroTotals, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MealAdherenceCheckIn } from "@/components/calendarization/meal-adherence-check-in";
import { snapshotAllocation, snapshotCalories } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { FoodPanels, type FoodPanelItem } from "@/components/panels";
import { Button, InlineNotice, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

function percentage(part: number | null | undefined, total: number | null | undefined): number {
  return total && total > 0 ? ((part ?? 0) / total) * 100 : 0;
}

function foodItems(meal: MealSnapshot): FoodPanelItem[] {
  const mealTotals = meal.totals;
  const mealCalories = snapshotCalories(mealTotals);
  return (meal.foods ?? []).map((food, index) => {
    const totals: MacroTotals = {
      protein_g: food.protein_g ?? 0,
      carbs_g: food.carbs_g ?? 0,
      fat_g: food.fat_g ?? 0,
      total_kcal: food.total_kcal ?? undefined,
    };
    const calories = snapshotCalories(totals);
    return {
      id: food.key ?? `food-${index}`,
      name: food.name ?? "Alimento",
      quantity: food.quantity_g ?? 0,
      quantityUnit: "g",
      calories,
      calorieShare: percentage(calories, mealCalories),
      proteinGrams: totals.protein_g ?? 0,
      carbsGrams: totals.carbs_g ?? 0,
      fatGrams: totals.fat_g ?? 0,
      proteinAllocation: percentage(totals.protein_g, mealTotals?.protein_g),
      carbsAllocation: percentage(totals.carbs_g, mealTotals?.carbs_g),
      fatAllocation: percentage(totals.fat_g, mealTotals?.fat_g),
    };
  });
}

export default function CalendarizedMealDetailScreen() {
  const { id, mealKey } = useLocalSearchParams<{ id: string; mealKey: string }>();
  const { status, apiRequest } = useSession();
  const [meal, setMeal] = useState<MealSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
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
      if (!match) setError("Esta comida ya no está disponible en el día calendarizado.");
    } catch (nextError) {
      setError(userFacingError(nextError));
      setMeal(null);
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
      entity: "meal",
      identityVisible: compactHeaderVisible,
      title: meal?.name ?? "Comida del programa",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, meal?.name, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !meal) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Cargando detalle…</Text></View>;
  if (!meal) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;

  const totals = meal.totals;
  const foods = foodItems(meal);
  return (
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
        indicators={[{ icon: "food", label: "alimentos", value: foods.length }]}
        nutrition={{
          calories: snapshotCalories(totals),
          carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
          fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
          protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: null },
        }}
        subtitle={meal.hour?.slice(0, 5)}
        title={meal.name ?? "Comida"}>
        <EntityDetailSection detail={`${foods.length} alimentos`} title="Tabla de comparación entre alimentos">
          <FoodPanels items={foods} />
        </EntityDetailSection>
        <MealAdherenceCheckIn dayId={dayId} mealKey={mealKey} />
      </EntityDetailPage>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
