import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { snapshotAllocation, snapshotCalories, snapshotMealPanelItem } from "@/components/calendarization/presentation-adapters";
import { EntityDetailPage, EntityDetailSection } from "@/components/details";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { NutritionEntityCard } from "@/components/nutrition";
import { MealPanels } from "@/components/panels";
import { Button, ContentPanel, EntityCardAction, InlineNotice, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function CalendarizedMealCards({ meals }: { meals: MealSnapshot[] }) {
  const router = useRouter();
  return (
    <View style={styles.mealCardList}>
      {meals.map((meal, index) => {
        const totals = meal.totals;
        return (
          <View key={meal.key ?? `${meal.name}-${index}`} style={styles.mealCardStep}>
            <View aria-hidden style={styles.mealCardMarker}>
              <View style={styles.mealCardLine} />
              <View style={styles.mealCardNumber}><Text style={styles.mealCardNumberText}>{index + 1}</Text></View>
            </View>
            <NutritionEntityCard
              actions={meal.detail_id ? (
                <EntityCardAction
                  label={`Ver detalle de ${meal.name ?? "la comida"}`}
                  onPress={() => router.push(`/libraries/meals/${meal.detail_id}` as Href)}
                  role="link">
                  <ChevronRight color={tokens.color.textMuted} size={23} strokeWidth={2.2} />
                </EntityCardAction>
              ) : null}
              entity="meal"
              indicators={[{ icon: "food", label: "alimentos", value: meal.foods?.length ?? 0 }]}
              nutrition={{
                calories: snapshotCalories(totals),
                carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
                fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
                protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: null },
              }}
              subtitle={meal.hour?.slice(0, 5)}
              title={meal.name ?? "Comida"}>
              <ContentPanel muted title="Alimentos de esta comida">
                {meal.foods?.length ? meal.foods.map((food, foodIndex) => (
                  <View key={food.key ?? `${food.name}-${foodIndex}`} style={[styles.foodRow, foodIndex === (meal.foods?.length ?? 0) - 1 && styles.foodRowLast]}>
                    <Text numberOfLines={2} style={styles.foodName}>{food.name ?? "Alimento"}</Text>
                    <Text style={styles.foodQuantity}>{food.quantity_g != null ? `${food.quantity_g.toLocaleString("es-CL", { maximumFractionDigits: 1 })} g` : "Sin cantidad"}</Text>
                  </View>
                )) : <Text style={textStyles.muted}>Esta comida no contiene alimentos detallados.</Text>}
              </ContentPanel>
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
    setHeaderPresentation({ mode: "library-detail", entity: "dailyPlan", identityVisible: compactHeaderVisible, title: day?.plan_snapshot?.name ?? day?.plan_name ?? "Detalle del día" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, day?.plan_name, day?.plan_snapshot?.name, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !day) return <View style={styles.loading}><ActivityIndicator color={tokens.color.interactivePrimary} size="large" /><Text style={textStyles.muted}>Abriendo el día…</Text></View>;
  if (!day) return <View style={styles.loading}>{error ? <InlineNotice tone="error">{error}</InlineNotice> : null}<Button label="Reintentar" onPress={() => void load()} variant="secondary" /></View>;

  const snapshot = day.plan_snapshot;
  const meals = snapshot?.meals ?? [];
  const totals = snapshot?.totals;
  const totalCalories = snapshotCalories(totals);
  const mealItems = meals.map((meal, index) => snapshotMealPanelItem(meal, index, totalCalories));

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      onScroll={({ nativeEvent }) => { const visible = nativeEvent.contentOffset.y > 1; if (visible !== compactHeaderVisible) setCompactHeaderVisible(visible); }}
      scrollEventThrottle={16}
      style={styles.screen}>
      {day.has_plan && snapshot ? (
        <EntityDetailPage
          entity="dailyPlan"
          eyebrow={displayDate(day.calendar_date)}
          indicators={[
            { icon: "day", label: "posición", value: `S${day.week_number} · D${day.day_number}` },
            { icon: "meal", label: "comidas", value: meals.length },
          ]}
          nutrition={{
            calories: totalCalories,
            carbs: { allocation: snapshotAllocation(totals, "carbs_g"), grams: totals?.carbs_g ?? 0 },
            fat: { allocation: snapshotAllocation(totals, "fat_g"), grams: totals?.fat_g ?? 0 },
            protein: { allocation: snapshotAllocation(totals, "protein_g"), grams: totals?.protein_g ?? 0, perKilogram: null },
          }}
          subtitle="Plan diario calendarizado"
          title={snapshot.name ?? day.plan_name ?? "Plan diario"}>
          <EntityDetailSection detail={`${meals.length} elementos`} title="Comidas en este plan">
            <MealPanels items={mealItems} />
          </EntityDetailSection>
          {meals.length ? (
            <EntityDetailSection detail={`${meals.length} comidas`} title="Detalle de cada Comida">
              <CalendarizedMealCards meals={meals} />
            </EntityDetailSection>
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
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, paddingBottom: 42, paddingHorizontal: tokens.spacing.screen, paddingTop: tokens.spacing.lg },
  foodName: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: "500" },
  foodQuantity: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontVariant: ["tabular-nums"] },
  foodRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minHeight: 42, paddingHorizontal: tokens.spacing.sm },
  foodRowLast: { borderBottomWidth: 0 },
  loading: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  mealCardLine: { backgroundColor: tokens.color.borderDefault, height: 1, width: "100%" },
  mealCardList: { gap: tokens.spacing.lg, minWidth: 0, width: "100%" },
  mealCardMarker: { alignItems: "center", height: 36, justifyContent: "center", paddingHorizontal: tokens.spacing.xs, position: "relative", width: "100%" },
  mealCardNumber: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, height: 36, justifyContent: "center", left: tokens.spacing.xs, position: "absolute", width: 36, zIndex: 1 },
  mealCardNumberText: { color: tokens.color.textMuted, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: "600" },
  mealCardStep: { gap: tokens.spacing.sm, minWidth: 0 },
  metadataLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption },
  metadataRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  metadataValue: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: "500", textAlign: "right", textTransform: "capitalize" },
  screen: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
});
