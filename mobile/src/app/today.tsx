import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { MealSnapshot, ProposalListData, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { MacroSummary } from "@/components/nutrition";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, ProgressBar, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { syncNativeReminders } from "@/notifications/native-reminders";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(
    new Date(`${value}T12:00:00`),
  );
}

function MealCard({ meal }: { meal: MealSnapshot }) {
  return (
    <Card muted style={styles.mealCard}>
      <View style={styles.mealHeader}>
        <View style={styles.mealCopy}>
          <Text style={styles.mealName}>{meal.name ?? "Comida"}</Text>
          <Text style={textStyles.caption}>{meal.foods?.length ?? 0} alimentos</Text>
        </View>
        {meal.hour ? <Pill color={tokens.color.meal} label={meal.hour} /> : null}
      </View>
      <View style={styles.miniMacros}>
        <Text style={[styles.miniMacro, { color: tokens.color.protein }]}>P {Math.round(meal.totals?.protein_g ?? 0)} g</Text>
        <Text style={[styles.miniMacro, { color: tokens.color.carbs }]}>C {Math.round(meal.totals?.carbs_g ?? 0)} g</Text>
        <Text style={[styles.miniMacro, { color: tokens.color.fat }]}>G {Math.round(meal.totals?.fat_g ?? 0)} g</Text>
      </View>
    </Card>
  );
}

export default function TodayScreen() {
  const router = useRouter();
  const { status, session, profile, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingProposalCount, setPendingProposalCount] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextToday = await apiRequest<TodayData>("/api/v1/today");
      setToday(nextToday);
      void apiRequest<ProposalListData>("/api/v1/proposals?status=pending_review&limit=1")
        .then((page) => setPendingProposalCount(page.pending_count))
        .catch(() => undefined);
      if (nextToday.reminders) {
        void syncNativeReminders(nextToday.reminders, apiRequest).catch(() => undefined);
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  if (status === "anonymous") return <Redirect href="/login" />;
  if (status === "authenticated" && profile?.review_disclosure_required) return <Redirect href="./disclosures" />;
  if (status === "authenticated" && !profile?.onboarding_completed) return <Redirect href="/onboarding" />;
  if (loading && !today) return <LoadingState />;

  const snapshot = today?.plan_snapshot;
  const meals = snapshot?.meals ?? [];
  const firstName = session?.display_name.split(" ")[0] || session?.username || "Atleta";

  return (
    <Screen>
      <AppHeader eyebrow={today ? displayDate(today.local_date) : "Hoy"} title={`Vamos, ${firstName}`} />
      {error ? (
        <InlineNotice tone="error">{error}</InlineNotice>
      ) : null}
      {today?.calendarization ? (
        <Card accent={tokens.color.program}>
          <View style={styles.programHeader}>
            <View style={styles.programCopy}>
              <Text style={styles.programName}>{today.calendarization.program_name}</Text>
              <Text style={textStyles.caption}>Día {today.calendarization.progress_day} de {today.calendarization.progress_total_days}</Text>
            </View>
            <Pill color={tokens.color.program} label={`${today.calendarization.progress_percent}%`} />
          </View>
          <ProgressBar value={today.calendarization.progress_percent} />
          <Button label="Abrir mi programa" onPress={() => router.push("/program" as Href)} variant="secondary" />
        </Card>
      ) : (
        <Card accent={tokens.color.program}>
          <SectionTitle title="Aún no hay programa activo" />
          <Text style={textStyles.muted}>Elige uno de tus programas y conviértelo en tu recorrido diario desde la app.</Text>
          <Button label="Calendarizar un programa" onPress={() => router.push("/program/activate" as Href)} />
        </Card>
      )}

      {today?.adherence ? (
        <Card accent={tokens.color.success}>
          <View style={styles.programHeader}>
            <View style={styles.programCopy}>
              <Text style={styles.planLabel}>ÚLTIMOS {today.adherence.days} DÍAS</Text>
              <Text style={styles.planName}>{today.adherence.adherence_percent}% de adherencia</Text>
            </View>
            <Pill
              color={tokens.color.success}
              label={`${today.adherence.completed_meals}/${today.adherence.planned_meals}`}
            />
          </View>
          <ProgressBar value={today.adherence.adherence_percent} />
          <Text style={textStyles.caption}>
            {today.adherence.skipped_meals} omitidas · {today.adherence.unrecorded_meals} aún sin registrar
          </Text>
          <Button label="Registrar revisión" onPress={() => router.push("./review")} variant="secondary" />
        </Card>
      ) : null}

      {today?.measurements?.latest_weight_kg != null ? (
        <Card muted>
          <SectionTitle detail={`${today.measurements.count} mediciones`} title="Tendencia del programa" />
          <View style={styles.measurementRow}>
            <Text style={styles.measurementValue}>{today.measurements.latest_weight_kg.toFixed(1)} kg</Text>
            {today.measurements.change_kg != null ? (
              <Pill
                color={tokens.color.protein}
                label={`${today.measurements.change_kg > 0 ? "+" : ""}${today.measurements.change_kg.toFixed(1)} kg`}
              />
            ) : null}
          </View>
        </Card>
      ) : null}

      {today?.pending_revision ? (
        <Card accent={tokens.color.warning}>
          <SectionTitle detail={`Desde ${today.pending_revision.effective_from}`} title="Ajuste para revisar" />
          <Text style={textStyles.muted}>{today.pending_revision.rationale}</Text>
          <Button label="Revisar antes de aplicar" onPress={() => router.push("./revision")} />
        </Card>
      ) : null}

      {pendingProposalCount > 0 ? (
        <Card accent={tokens.color.warning}>
          <SectionTitle detail={`${pendingProposalCount} pendientes`} title="Propuestas para revisar" />
          <Text style={textStyles.muted}>El Asistente preparó resultados que aún no modifican tu librería.</Text>
          <Button label="Abrir Propuestas" onPress={() => router.push("/proposals" as Href)} />
        </Card>
      ) : null}

      {today?.has_plan && snapshot ? (
        <>
          <Card accent={tokens.color.dailyPlan}>
            <View style={styles.planHeader}>
              <View style={styles.programCopy}>
                <Text style={styles.planLabel}>PLAN DE HOY</Text>
                <Text style={styles.planName}>{snapshot.name ?? "Plan diario"}</Text>
              </View>
              <Pill color={tokens.color.dailyPlan} label={`${meals.length} comidas`} />
            </View>
            <MacroSummary totals={snapshot.totals} />
          </Card>
          <SectionTitle detail="Horario local" title="Comidas previstas" />
          {meals.map((meal, index) => <MealCard key={meal.key ?? `${meal.name}-${index}`} meal={meal} />)}
          <Button label="Abrir check-in del día" onPress={() => router.push("/check-in")} />
        </>
      ) : (
        <Card muted>
          <SectionTitle title="Día sin plan" />
          <Text style={textStyles.muted}>Tu calendarización no tiene un plan nutricional previsto para esta fecha.</Text>
        </Card>
      )}
      <Button label="Registrar peso" onPress={() => router.push("/weight")} variant="secondary" />
      <Button label="Digitalizar etiqueta nutricional" onPress={() => router.push("./label-capture")} variant="secondary" />
      <Button label="Mi suscripción" onPress={() => router.push("./subscription")} variant="secondary" />
      <Button label="Cuenta, privacidad y ayuda" onPress={() => router.push("./account")} variant="secondary" />
      {today?.reminders ? (
        <Button label="Configurar recordatorios" onPress={() => router.push("./reminders")} variant="secondary" />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  programHeader: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between" },
  programCopy: { flex: 1, gap: 4 },
  programName: { color: tokens.color.textMain, fontSize: 18, fontWeight: "800" },
  planHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  planLabel: { color: tokens.color.dailyPlan, fontSize: 11, fontWeight: "900", letterSpacing: 1.2 },
  planName: { color: tokens.color.textMain, fontSize: 22, fontWeight: "800" },
  mealCard: { borderLeftColor: tokens.color.meal, borderLeftWidth: 3 },
  mealHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  mealCopy: { gap: 3 },
  mealName: { color: tokens.color.textMain, fontSize: 17, fontWeight: "800" },
  miniMacros: { flexDirection: "row", gap: 15 },
  miniMacro: { fontSize: 12, fontWeight: "800" },
  measurementRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  measurementValue: { color: tokens.color.textMain, fontSize: 28, fontWeight: "900", fontVariant: ["tabular-nums"] },
});
