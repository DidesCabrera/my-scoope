import { Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";

import { userFacingError } from "@/api/errors";
import type { CalendarizationHistoryData, CalendarizationStatus } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { EntityCard, LoadingState, Pill, Screen, SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";

const statusLabels: Record<CalendarizationStatus, string> = {
  active: "Activo",
  cancelled: "Cancelado",
  completed: "Completado",
  paused: "Pausado",
  scheduled: "Programado",
};

const statusColors: Record<CalendarizationStatus, string> = {
  active: tokens.color.success,
  cancelled: tokens.color.danger,
  completed: tokens.color.success,
  paused: tokens.color.warning,
  scheduled: tokens.color.program,
};

function displayDate(value: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T12:00:00`));
}

export default function ProgramHistoryScreen() {
  const { status, apiRequest } = useSession();
  const [history, setHistory] = useState<CalendarizationHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const setHeaderPresentation = useHeaderPresentation();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setHistory(await apiRequest<CalendarizationHistoryData>("/api/v1/program/calendarizations/history?limit=50"));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/program", mode: "back", title: "Historial de programas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));
  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading && !history) return <LoadingState label="Cargando tu historial…" />;

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      <SectionHeading detail={`${history?.count ?? 0}`} title="Programas anteriores" />
      {history?.items.length ? history.items.map((item) => (
        <EntityCard
          accessory={<Pill color={statusColors[item.status]} label={statusLabels[item.status]} />}
          entity="program"
          eyebrow="Programa anterior"
          indicators={[{ icon: "dailyPlan", label: "días con plan", value: `${item.days_with_plan}/${item.days_total}` }]}
          key={item.id}
          subtitle={`${displayDate(item.start_date)} – ${displayDate(item.end_date)} · ${item.timezone_name}`}
          title={item.program_name}
        />
      )) : (
        <EmptyState message="Tus programas finalizados o cancelados aparecerán aquí." title="Aún no hay programas anteriores" />
      )}
    </Screen>
  );
}
