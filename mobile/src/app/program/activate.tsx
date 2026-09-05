import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { Search } from "lucide-react-native";
import { useCallback, useMemo, useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MobileApiError, userFacingError } from "@/api/errors";
import type { CalendarizationActivationData, CalendarizationActivationInput, LibraryItem, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ProgramChildCard, programDailyMetricData } from "@/components/libraries/program-child-card";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { PickerEntryTabs } from "@/components/pickers/picker-entry-tabs";
import { ConfirmationState, EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { Button, Card, ChoiceRow, Field, LoadingState, Screen, SectionHeading } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { refreshNativeReminders } from "@/notifications/native-reminders";

type Toggle = "on" | "off";
type Confirmation = { kind: "incomplete" | "replacement"; message: string } | null;

const toggleOptions: { value: Toggle; label: string }[] = [{ value: "on", label: "Sí" }, { value: "off", label: "No" }];

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function indicatorValue(program: LibraryItem, icon: "week" | "dailyPlan" | "food"): number {
  const value = program.indicators.find((indicator) => indicator.icon === icon)?.value;
  return typeof value === "number" ? value : Number.parseInt(String(value ?? 0), 10) || 0;
}

export default function ActivateProgramScreen() {
  const router = useRouter();
  const { programId } = useLocalSearchParams<{ programId?: string }>();
  const requestedProgramId = Number(programId);
  const { status, profile, apiRequest } = useSession();
  const [programs, setPrograms] = useState<LibraryItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [startDate, setStartDate] = useState(localDate);
  const [timezoneName, setTimezoneName] = useState(profile?.timezone_name || "UTC");
  const [dailyTime, setDailyTime] = useState("07:00");
  const [daily, setDaily] = useState<Toggle>("on");
  const [meals, setMeals] = useState<Toggle>("off");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation>(null);
  const setHeaderPresentation = useHeaderPresentation();

  const selected = useMemo(() => programs.find((program) => program.id === selectedId) ?? null, [programs, selectedId]);
  const filteredPrograms = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("es");
    if (!normalizedQuery) return programs;
    return programs.filter((program) => `${program.name} ${program.subtitle ?? ""}`.toLocaleLowerCase("es").includes(normalizedQuery));
  }, [programs, query]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await apiRequest<LibraryPageData>("/api/v1/library/programs?limit=100");
      const eligiblePrograms = page.items.filter((program) => program.can_calendarize);
      setPrograms(eligiblePrograms);
      setSelectedId(Number.isInteger(requestedProgramId) && eligiblePrograms.some((program) => program.id === requestedProgramId) ? requestedProgramId : null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, requestedProgramId]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));
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
          contentContainerStyle={styles.selectionScrollContent}
          keyboardDismissMode="on-drag"
          keyboardShouldPersistTaps="handled"
          stickyHeaderIndices={[0]}>
          <View style={styles.selectionSticky}>
            <PickerEntryTabs
              createLabel="Crear Nuevo"
              onCreate={() => router.push({ pathname: "/libraries/create", params: { entity: "program" } })}
            />
            <View style={styles.searchField}>
              <Search color={tokens.color.textSoft} size={19} />
              <TextInput
                accessibilityLabel="Buscar programa"
                autoCapitalize="words"
                onChangeText={setQuery}
                placeholder="Escribe el nombre de un programa"
                placeholderTextColor={tokens.color.textSubtle}
                style={styles.searchInput}
                value={query}
              />
            </View>
          </View>

          <View style={styles.options}>
            <SectionHeading detail={`${filteredPrograms.length} disponibles`} title="Selecciona un programa" />
            {filteredPrograms.map((program) => (
              <ProgramChildCard
                axisLabels={program.panel.kind === "weeks" ? program.panel.weeks.map((week) => `S${week.week_number}`) : []}
                filledDaysCount={indicatorValue(program, "dailyPlan")}
                foodsCount={indicatorValue(program, "food")}
                key={program.id}
                metricData={program.panel.kind === "weeks" ? programDailyMetricData(program.panel.weeks) : []}
                onOpen={() => router.push(`/program/activate?programId=${program.id}` as Href)}
                openActionLabel="Seleccionar"
                owner={program.creator}
                title={program.name}
                weeksCount={indicatorValue(program, "week")}
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
            axisLabels={selected.panel.kind === "weeks" ? selected.panel.weeks.map((week) => `S${week.week_number}`) : []}
            filledDaysCount={indicatorValue(selected, "dailyPlan")}
            foodsCount={indicatorValue(selected, "food")}
            metricData={selected.panel.kind === "weeks" ? programDailyMetricData(selected.panel.weeks) : []}
            onOpen={() => router.replace("/program/activate" as Href)}
            openActionLabel="Cambiar selección"
            owner={selected.creator}
            title={selected.name}
            weeksCount={indicatorValue(selected, "week")}
          />

          <Card accent={tokens.color.program}>
            <SectionHeading title="Configura la selección" />
            <Field keyboardType="numbers-and-punctuation" label="Fecha de inicio (AAAA-MM-DD)" onChangeText={(value) => { setStartDate(value); setConfirmation(null); }} placeholder="2026-08-13" value={startDate} />
            <Field label="Zona horaria IANA" onChangeText={setTimezoneName} placeholder="America/Santiago" value={timezoneName} />
            <Field keyboardType="numbers-and-punctuation" label="Hora del aviso diario" onChangeText={setDailyTime} placeholder="07:00" value={dailyTime} />
            <ChoiceRow<Toggle> label="Aviso del plan diario" onChange={setDaily} options={toggleOptions} value={daily} />
            <ChoiceRow<Toggle> label="Avisos según la hora de cada comida" onChange={setMeals} options={toggleOptions} value={meals} />
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
  emptyText: { color: tokens.color.textMuted, fontSize: tokens.type.body },
  options: { gap: tokens.spacing.lg, paddingHorizontal: tokens.spacing.screen },
  searchField: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, marginHorizontal: tokens.spacing.screen, minHeight: 38, paddingHorizontal: tokens.spacing.md },
  searchInput: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, minHeight: 36, paddingVertical: 0 },
  selectionSafeArea: { backgroundColor: tokens.color.surfaceApp, flex: 1 },
  selectionScrollContent: { flexGrow: 1, paddingBottom: 42 },
  selectionSticky: { backgroundColor: tokens.color.surfaceApp, gap: tokens.spacing.xs, paddingBottom: tokens.spacing.lg, zIndex: 2 },
});
