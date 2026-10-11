import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MobileApiError, userFacingError } from "@/api/errors";
import type { CalendarizationActivationData, CalendarizationActivationInput, CalendarizationProgramOption, CalendarizationProgramOptionsData, LibraryItem, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProgramChildCard, programDailyMetricData } from "@/components/libraries/program-child-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { ConfirmationState, EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, LoadingState, NativeDateTimeField, Screen, SearchField, SectionHeading, SystemSwitch } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

type Toggle = "on" | "off";
type Confirmation = { kind: "incomplete" | "replacement"; message: string } | null;

function legacyIndicatorValue(program: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = program.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

function legacyCalendarizationOption(program: LibraryItem): CalendarizationProgramOption {
  return {
    creator: program.creator,
    filled_days_count: legacyIndicatorValue(program, "dailyPlan"),
    foods_count: legacyIndicatorValue(program, "food"),
    id: program.id,
    name: program.name,
    weeks: program.panel.kind === "weeks" ? program.panel.weeks : [],
    weeks_count: legacyIndicatorValue(program, "week"),
  };
}

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function detectedTimezone(profileTimezone?: string | null): string {
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (timezone) return timezone;
  } catch {
    // Fall back to the last known profile timezone on runtimes without Intl timezone support.
  }
  return profileTimezone?.trim() || "UTC";
}

function NotificationToggle({ label, onValueChange, value }: { label: string; onValueChange(value: boolean): void; value: boolean }) {
  return (
    <View style={styles.notificationRow}>
      <Text style={styles.notificationLabel}>{label}</Text>
      <SystemSwitch accessibilityLabel={label} onValueChange={onValueChange} value={value} />
    </View>
  );
}

export default function ActivateProgramScreen() {
  const router = useRouter();
  const { programId } = useLocalSearchParams<{ programId?: string }>();
  const requestedProgramId = Number(programId);
  const { status, profile, apiRequest } = useSession();
  const [programs, setPrograms] = useState<CalendarizationProgramOption[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [startDate, setStartDate] = useState(localDate);
  const [timezoneName, setTimezoneName] = useState(() => detectedTimezone(profile?.timezone_name));
  const [dailyTime, setDailyTime] = useState("07:00");
  const [daily, setDaily] = useState<Toggle>("on");
  const [meals, setMeals] = useState<Toggle>("on");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation>(null);
  const setHeaderPresentation = useHeaderPresentation();

  const selected = useMemo(() => programs.find((program) => program.id === selectedId) ?? null, [programs, selectedId]);
  const filteredPrograms = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("es");
    if (!normalizedQuery) return programs;
    return programs.filter((program) => program.name.toLocaleLowerCase("es").includes(normalizedQuery));
  }, [programs, query]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let page: CalendarizationProgramOptionsData;
      try {
        page = await apiRequest<CalendarizationProgramOptionsData>("/api/v1/library/programs/calendarization-options?limit=100");
      } catch (nextError) {
        if (!(nextError instanceof MobileApiError) || ![404, 422].includes(nextError.status)) throw nextError;
        const legacyPage = await apiRequest<LibraryPageData>("/api/v1/library/programs?limit=100");
        page = { ...legacyPage, items: legacyPage.items.filter((program) => program.can_calendarize).map(legacyCalendarizationOption) };
      }
      setPrograms(page.items);
      setSelectedId(Number.isInteger(requestedProgramId) && page.items.some((program) => program.id === requestedProgramId) ? requestedProgramId : null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, requestedProgramId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
  useFocusEffect(useCallback(() => {
    setTimezoneName(detectedTimezone(profile?.timezone_name));
  }, [profile?.timezone_name]));
  useFocusEffect(useCallback(() => {
    const cancel = () => router.dismissTo("/program" as Href);
    setHeaderPresentation({ action: { label: "Cancelar", onPress: cancel }, fallback: "/program", mode: "back", title: "Calendarizar programa" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [router, setHeaderPresentation]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Buscando tus programas…" />;

  if (programs.length && !selected) {
    return (
      <SafeAreaView edges={["left", "right"]} style={styles.selectionSafeArea}>
        <ScrollView
          automaticallyAdjustKeyboardInsets
          contentContainerStyle={styles.selectionScrollContent}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          stickyHeaderIndices={[0]}>
          <View style={styles.selectionSticky}>
            <PickerEntryTabs
              createLabel="Crear Nuevo"
              onCreate={() => router.push({ pathname: "/libraries/create", params: { entity: "program" } })}
            />
            <SearchField accessibilityLabel="Buscar programa" autoCapitalize="words" bleed onChangeText={setQuery} placeholder="Escribe el nombre de un programa" value={query} />
          </View>

          <View style={styles.options}>
            <SectionHeading detail={`${filteredPrograms.length} disponibles`} title="Selecciona un programa" />
            {filteredPrograms.map((program) => (
              <ProgramChildCard
                axisLabels={program.weeks.map((week) => `S${week.week_number}`)}
                filledDaysCount={program.filled_days_count}
                foodsCount={program.foods_count}
                key={program.id}
                metricData={programDailyMetricData(program.weeks)}
                onOpen={() => router.push(`/program/activate?programId=${program.id}` as Href)}
                openActionLabel="Seleccionar"
                title={program.name}
                weeksCount={program.weeks_count}
              />
            ))}
            {!filteredPrograms.length ? <Text style={styles.emptyText}>No encontramos programas con ese nombre.</Text> : null}
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  async function activate(overrides: Partial<Pick<CalendarizationActivationInput, "confirm_incomplete" | "replace_current">> = {}) {
    if (!selectedId) return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      setError("Usa una fecha válida en formato AAAA-MM-DD.");
      return;
    }
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(dailyTime)) {
      setError("Usa una hora válida en formato HH:MM.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload: CalendarizationActivationInput = {
        program_id: selectedId,
        start_date: startDate,
        timezone_name: timezoneName,
        daily_notification_time: dailyTime,
        daily_notifications_enabled: daily === "on",
        meal_notifications_enabled: meals === "on",
        confirm_incomplete: confirmation?.kind === "incomplete" || confirmation?.kind === "replacement" || Boolean(overrides.confirm_incomplete),
        replace_current: confirmation?.kind === "replacement" || Boolean(overrides.replace_current),
      };
      await apiRequest<CalendarizationActivationData>("/api/v1/program/calendarizations", { method: "POST", body: JSON.stringify(payload) });
      try {
        await refreshNativeReminders(apiRequest, { requestPermission: daily === "on" || meals === "on" });
      } catch {
        router.replace("/reminders" as Href);
        return;
      }
      router.replace("/program" as Href);
    } catch (nextError) {
      if (nextError instanceof MobileApiError && nextError.code === "calendarization_incomplete_confirmation_required") {
        const count = Number(nextError.details.empty_count ?? 0);
        setConfirmation({ kind: "incomplete", message: `Este programa tiene ${count} ${count === 1 ? "día" : "días"} sin plan. Esos días se mostrarán vacíos en tu recorrido.` });
      } else if (nextError instanceof MobileApiError && nextError.code === "calendarization_replacement_confirmation_required") {
        const currentName = String(nextError.details.current_program_name || "tu programa actual");
        setConfirmation({ kind: "replacement", message: `Ya estás siguiendo “${currentName}”. Al continuar, ese recorrido se cancelará y quedará en tu historial.` });
      } else {
        setError(userFacingError(nextError));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen headerMode="preserve">
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {!programs.length ? (
        <EmptyState actionLabel="Ir a mis programas" message="Guarda primero un programa semanal para poder calendarizarlo." onAction={() => router.replace("/libraries/programs")} title="No hay programas disponibles" />
      ) : selected ? (
        <>
          <ProgramChildCard
            axisLabels={selected.weeks.map((week) => `S${week.week_number}`)}
            filledDaysCount={selected.filled_days_count}
            foodsCount={selected.foods_count}
            metricData={programDailyMetricData(selected.weeks)}
            title={selected.name}
            weeksCount={selected.weeks_count}
          />

          <Card>
            <SectionHeading title="Configura la selección" />
            <NativeDateTimeField label="Fecha de inicio" minimumValue={localDate()} mode="date" onChange={(value) => { setStartDate(value); setConfirmation(null); }} value={startDate} />
            <View style={styles.dailyNotificationBlock}>
              <NotificationToggle
                label="Aviso inicial del plan diario"
                onValueChange={(enabled) => setDaily(enabled ? "on" : "off")}
                value={daily === "on"}
              />
              {daily === "on" ? <NativeDateTimeField hideLabel label="Hora del aviso diario" minuteInterval={5} mode="time" onChange={setDailyTime} value={dailyTime} /> : null}
            </View>
            <NotificationToggle
              label="Avisos según la hora de cada comida"
              onValueChange={(enabled) => setMeals(enabled ? "on" : "off")}
              value={meals === "on"}
            />
          </Card>
          {confirmation ? (
            <ConfirmationState busy={saving} confirmLabel={confirmation.kind === "replacement" ? "Cambiar programa" : "Continuar igualmente"} danger={confirmation.kind === "replacement"} message={confirmation.message} onCancel={() => setConfirmation(null)} onConfirm={() => void activate(confirmation.kind === "incomplete" ? { confirm_incomplete: true } : { replace_current: true })} title={confirmation.kind === "replacement" ? "¿Reemplazar tu programa actual?" : "Este programa está incompleto"} />
          ) : <Button bleed label="Calendarizar programa" loading={saving} onPress={() => void activate()} />}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  dailyNotificationBlock: { gap: tokens.spacing.xs },
  emptyText: { color: tokens.color.textMuted, fontSize: tokens.type.body },
  notificationLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  notificationRow: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", minHeight: 44 },
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  selectionSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  selectionScrollContent: { flexGrow: 1, paddingBottom: 42 },
  selectionSticky: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen, zIndex: 2 },
});
