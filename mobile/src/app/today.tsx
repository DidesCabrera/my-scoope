import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData, ProposalListData, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedDailyPlanCard } from "@/components/calendarization/calendarized-daily-plan-card";
import { CurrentWeekSection } from "@/components/calendarization/current-week-section";
import { HomeActions } from "@/components/home-actions";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProgramActiveHomeOverview } from "@/components/programs/program-active-card";
import { AppHeader, Button, Card, InlineNotice, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { syncNativeRemindersForProgram } from "@/notifications/native-reminders";

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { weekday: "long", day: "numeric", month: "long" }).format(
    new Date(`${value}T12:00:00`),
  );
}

export default function TodayScreen() {
  const router = useRouter();
  const { status, session, profile, apiRequest } = useSession();
  const [today, setToday] = useState<TodayData | null>(null);
  const [activeProgram, setActiveProgram] = useState<ActiveProgramData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [homeActionsVisible, setHomeActionsVisible] = useState(false);
  const [pendingProposalCount, setPendingProposalCount] = useState(0);
  const setHeaderPresentation = useHeaderPresentation();
  const openHomeActions = useCallback(() => setHomeActionsVisible(true), []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextToday, nextProgram] = await Promise.all([
        apiRequest<TodayData>("/api/v1/today"),
        apiRequest<ActiveProgramData>("/api/v1/program/active"),
      ]);
      setToday(nextToday);
      setActiveProgram(nextProgram);
      void apiRequest<ProposalListData>("/api/v1/proposals?status=pending_review&limit=1")
        .then((page) => setPendingProposalCount(page.pending_count))
        .catch(() => undefined);
      if (nextToday.reminders) {
        void syncNativeRemindersForProgram(
          nextToday.reminders,
          nextToday.calendarization?.status ?? null,
          apiRequest,
        ).catch(() => undefined);
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

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ action: { label: "Acciones de inicio", onPress: openHomeActions }, mode: "default" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [openHomeActions, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (status === "authenticated" && profile?.review_disclosure_required) return <Redirect href="./disclosures" />;
  if (status === "authenticated" && !profile?.onboarding_completed) return <Redirect href="/onboarding" />;
  if (loading && !today) return <LoadingState />;

  const snapshot = today?.plan_snapshot;
  const todayProgramDay = activeProgram?.days.find((day) => day.id === today?.day_id);
  const firstName = session?.display_name.split(" ")[0] || session?.username || "Atleta";

  return (
    <>
      <Screen headerMode="preserve">
      <AppHeader eyebrow={today ? displayDate(today.local_date) : "Hoy"} title={`Vamos, ${firstName}`} />
      {today ? <CurrentWeekSection localDate={today.local_date} /> : null}

      {today?.has_plan && snapshot ? (
        <CalendarizedDailyPlanCard
          dayId={today.day_id}
          eyebrow="PLAN DE HOY"
          mealExecution={today.meal_execution}
          position={todayProgramDay ? { dayNumber: todayProgramDay.day_number, weekNumber: todayProgramDay.week_number } : undefined}
          snapshot={snapshot}
        />
      ) : (
        <Card muted>
          <SectionTitle title="Día sin plan" />
          <Text style={textStyles.muted}>Tu calendarización no tiene un plan nutricional previsto para esta fecha.</Text>
        </Card>
      )}

      {activeProgram?.calendarization ? (
        <ProgramActiveHomeOverview calendarization={activeProgram.calendarization} program={activeProgram} />
      ) : (
        <Card accent={tokens.color.program}>
          <SectionTitle title="Aún no hay programa activo" />
          <Text style={textStyles.muted}>Elige uno de tus programas y conviértelo en tu recorrido diario desde la app.</Text>
          <Button label="Calendarizar un programa" onPress={() => router.push("/program/activate" as Href)} />
        </Card>
      )}

      {error ? (
        <InlineNotice tone="error">{error}</InlineNotice>
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

      </Screen>
      <HomeActions
        onCaptureLabel={() => router.push("/label-capture")}
        onClose={() => setHomeActionsVisible(false)}
        onRegisterWeight={() => router.push("/weight")}
        visible={homeActionsVisible}
      />
    </>
  );
}

const styles = StyleSheet.create({
  measurementRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between" },
  measurementValue: { color: tokens.color.textMain, fontSize: 28, fontWeight: "900", fontVariant: ["tabular-nums"] },
});
