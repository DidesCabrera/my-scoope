import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealExecutionItem, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { snapshotAllocation, snapshotCalories, snapshotDailyPlanFoodPanelItems, snapshotFoodPanelItems, snapshotMealPanelItem } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { FoodPanels, MealPanels } from "@/components/panels";
import { Button, ContentPanel, EntityCardAction, InlineNotice, SectionDivider, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function completionFor(items: MealExecutionItem[]) {
  return {
    completedCount: items.filter((item) => item.status === "completed").length,
    noteCount: items.filter((item) => item.note.trim()).length,
  };
}

function CalendarizedMealCards({ dayId, mealExecution, meals }: { dayId: number; mealExecution: MealExecutionItem[]; meals: MealSnapshot[] }) {
  const router = useRouter();
  return (
    <View style={styles.mealCardList}>
      {meals.map((meal, index) => {
        const totals = meal.totals;
        const foods = snapshotFoodPanelItems(meal);
        const execution = mealExecution.find((item) => item.meal_key === meal.key);
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
              completion={{
                completedCount: execution?.status === "completed" ? 1 : 0,
                noteCount: execution?.note.trim() ? 1 : 0,
              }}
              entity="meal"
              eyebrow={`Comida ${index + 1}`}
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
              <FoodPanels items={foods} />
            </NutritionEntityCard>
          </View>
        );
      })}
    </View>
  );
}

export default function ProgramDayScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const [day, setDay] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const [actionsVisible, setActionsVisible] = useState(false);
  const setHeaderPresentation = useHeaderPresentation();

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setDay(await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${id}`));
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
  const mealItems = meals.map((meal, index) => snapshotMealPanelItem(meal, index, totalCalories));
  const foods = snapshotDailyPlanFoodPanelItems(meals);

  return (
    <>
    <ScrollView
      contentContainerStyle={styles.content}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollEventThrottle={16}
      style={styles.screen}>
      {day.has_plan && snapshot ? (
        <EntityDetailPage
          entity="dailyPlan"
          completion={completionFor(day.meal_execution)}
          eyebrow={displayDate(day.calendar_date)}
          indicators={[
            { icon: "day", label: "posición", value: `S${day.week_number} · D${day.day_number}` },
            { icon: "meal", label: "comidas", value: meals.length },
          ]}
          nutrition={{
            calories: totalCalories,
            carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
            fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
            protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: totals?.protein_per_kilogram ?? null },
          }}
          title={snapshot.name ?? day.plan_name ?? "Plan diario"}>
          <EntityDetailSection detail={`${meals.length} elementos`} title="Tabla de comparación entre comidas">
            <MealPanels items={mealItems} />
          </EntityDetailSection>
          {meals.length ? (
            <>
              <SectionDivider />
              <EntityDetailSection detail={`${meals.length} comidas`} title="Detalle de cada Comida">
                <CalendarizedMealCards dayId={day.id} mealExecution={day.meal_execution} meals={meals} />
              </EntityDetailSection>
            </>
          ) : null}
          {foods.length ? (
            <>
              <SectionDivider />
              <EntityDetailSection detail={`${foods.length} alimentos`} title="Alimentos en este plan diario">
                <FoodPanels items={foods} />
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
    </ScrollView>
    <CalendarizedEntityActions
      entityName={snapshot?.name ?? day.plan_name ?? "Plan diario"}
      onVisibleChange={setActionsVisible}
      rename={{
        onSubmit: async (name) => {
          setDay(await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${day.id}`, {
            body: JSON.stringify({ name }),
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          }));
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
  mealCardList: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  metadataLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  metadataRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  metadataValue: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: "500", textAlign: "right", textTransform: "capitalize" },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
