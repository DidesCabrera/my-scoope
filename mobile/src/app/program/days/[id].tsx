import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizedDayDetail, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MacroSummary } from "@/components/nutrition/macro-summary";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, Card, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${value}T12:00:00`));
}

function MealDetail({ meal }: { meal: MealSnapshot }) {
  return (
    <Card muted style={styles.meal}>
      <View style={styles.row}>
        <View style={styles.copy}>
          <Text style={styles.mealName}>{meal.name || "Comida"}</Text>
          <Text style={textStyles.caption}>{meal.foods?.length ?? 0} alimentos</Text>
        </View>
        {meal.hour ? <Pill color={tokens.color.meal} label={meal.hour.slice(0, 5)} /> : null}
      </View>
      {meal.totals ? <MacroSummary totals={meal.totals} /> : null}
      {meal.foods?.length ? (
        <View style={styles.foods}>
          {meal.foods.map((food, index) => (
            <View key={food.key ?? `${food.name}-${index}`} style={styles.food}>
              <Text style={styles.foodName}>{food.name || "Alimento"}</Text>
              <Text style={textStyles.caption}>{food.quantity_g != null ? `${Math.round(food.quantity_g)} g` : "Cantidad no indicada"}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </Card>
  );
}

export default function ProgramDayScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { status, apiRequest } = useSession();
  const [day, setDay] = useState<CalendarizedDayDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !day) return <LoadingState label="Abriendo el día…" />;

  const snapshot = day?.plan_snapshot;
  const meals = snapshot?.meals ?? [];

  return (
    <Screen>
      <AppHeader eyebrow={day ? displayDate(day.calendar_date) : "Mi programa"} title={snapshot?.name || day?.plan_name || "Detalle del día"} />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {day ? <Pill color={tokens.color.program} label={`Semana ${day.week_number} · Día ${day.day_number}`} /> : null}
      {day?.has_plan && snapshot ? (
        <>
          <Card accent={tokens.color.dailyPlan}>
            <View style={styles.row}>
              <View style={styles.copy}><Text style={styles.planLabel}>PLAN CALENDARIZADO</Text><Text style={styles.planName}>{snapshot.name || "Plan diario"}</Text></View>
              <Pill color={tokens.color.dailyPlan} label={`${meals.length} comidas`} />
            </View>
            <MacroSummary totals={snapshot.totals} />
          </Card>
          <SectionTitle detail={`${meals.length}`} title="Comidas previstas" />
          {meals.length ? meals.map((meal, index) => <MealDetail key={meal.key ?? `${meal.name}-${index}`} meal={meal} />) : <Text style={textStyles.muted}>Este plan no contiene comidas detalladas.</Text>}
        </>
      ) : day ? (
        <EmptyState message="La calendarización conserva este espacio, pero el programa no tiene un plan nutricional asignado para la fecha." title="Día sin plan" />
      ) : null}
      <Button label="Volver a Mi programa" onPress={() => { if (router.canGoBack()) router.back(); else router.replace("/program" as Href); }} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: 4 },
  food: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingTop: 10 },
  foodName: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: "700" },
  foods: { gap: 10 },
  meal: { borderLeftColor: tokens.color.meal, borderLeftWidth: 3 },
  mealName: { color: tokens.color.textMain, fontSize: 18, fontWeight: "800" },
  planLabel: { color: tokens.color.dailyPlan, fontSize: 11, fontWeight: "900", letterSpacing: 1.1 },
  planName: { color: tokens.color.textMain, fontSize: 22, fontWeight: "900" },
  row: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
});
