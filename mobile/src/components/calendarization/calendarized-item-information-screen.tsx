import { type Href, Redirect, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ActiveProgramData, CalendarizedDayDetail, CalendarizationStatus, MealSnapshot } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ContentPanel, LoadingState, Screen } from "@/components/ui";
import { RecoverableErrorState } from "@/components/ui/screen-states";
import { tokens } from "@/design/tokens";

import { compactDateLabel } from "./current-week";
import { normalizeActiveProgramData, normalizeCalendarizedDayDetail } from "./runtime-normalization";

type InformationEntity = "program" | "dailyPlan" | "meal";
type InformationRow = { label: string; value: string };

const statusLabels: Record<CalendarizationStatus, string> = {
  active: "Activo",
  cancelled: "Cancelado",
  completed: "Completado",
  paused: "Pausado",
  scheduled: "Programado",
};

export function CalendarizedItemInformationScreen({ entity }: { entity: InformationEntity }) {
  const { id, mealKey } = useLocalSearchParams<{ id?: string; mealKey?: string }>();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [rows, setRows] = useState<InformationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (entity === "program") {
        const result = normalizeActiveProgramData(await apiRequest<ActiveProgramData>("/api/v1/program/active"));
        const calendarization = result.calendarization;
        setRows(calendarization ? [
          { label: "Estado", value: statusLabels[calendarization.status] },
          { label: "Periodo", value: `${compactDateLabel(calendarization.start_date)} — ${compactDateLabel(calendarization.end_date)}` },
          { label: "Zona horaria", value: calendarization.timezone_name },
          { label: "Progreso", value: `${calendarization.progress_day} de ${calendarization.progress_total_days} días` },
        ] : []);
        return;
      }

      const dayId = Number(id);
      const day = normalizeCalendarizedDayDetail(await apiRequest<CalendarizedDayDetail>(`/api/v1/program/days/${dayId}`));
      if (!day) throw new Error("No fue posible cargar la información del elemento.");
      if (entity === "dailyPlan") {
        setRows([
          { label: "Fecha", value: compactDateLabel(day.calendar_date) },
          { label: "Ubicación", value: `Semana ${day.week_number} · Día ${day.day_number}` },
        ]);
        return;
      }

      const meal: MealSnapshot | undefined = day.plan_snapshot?.meals?.find((item) => item.key === mealKey);
      setRows(meal ? [
        { label: "Horario", value: meal.hour?.slice(0, 5) || "Sin horario" },
        { label: "Ubicación", value: `Semana ${day.week_number} · Día ${day.day_number}` },
      ] : []);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, entity, id, mealKey]);

  const fallback = entity === "program"
    ? "/program"
    : entity === "dailyPlan"
      ? `/program/days/${id}`
      : `/program/days/${id}/meals/${encodeURIComponent(mealKey ?? "")}`;

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: fallback as Href, mode: "back", title: "Información del elemento" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [fallback, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Abriendo la información…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {!error ? (
        <ContentPanel muted title="Información del elemento">
          {rows.map((row) => (
            <View key={row.label} style={styles.row}>
              <Text style={styles.label}>{row.label}</Text>
              <Text style={styles.value}>{row.value}</Text>
            </View>
          ))}
        </ContentPanel>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  label: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  value: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, textAlign: "right" },
});
