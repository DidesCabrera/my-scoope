import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { MobileApiError, userFacingError } from "@/api/errors";
import type { CalendarizationActivationData, CalendarizationActivationInput, LibraryItem, LibraryPageData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { ConfirmationState, EmptyState, RecoverableErrorState } from "@/components/ui/screen-states";
import { AppHeader, Button, Card, ChoiceRow, Field, LoadingState, Pill, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type Toggle = "on" | "off";
type Confirmation = { kind: "incomplete" | "replacement"; message: string } | null;

const toggleOptions: { value: Toggle; label: string }[] = [{ value: "on", label: "Sí" }, { value: "off", label: "No" }];

function localDate(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export default function ActivateProgramScreen() {
  const router = useRouter();
  const { programId } = useLocalSearchParams<{ programId?: string }>();
  const { status, profile, apiRequest } = useSession();
  const [programs, setPrograms] = useState<LibraryItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(programId ? Number(programId) : null);
  const [startDate, setStartDate] = useState(localDate);
  const [timezoneName, setTimezoneName] = useState(profile?.timezone_name || "UTC");
  const [dailyTime, setDailyTime] = useState("07:00");
  const [daily, setDaily] = useState<Toggle>("on");
  const [meals, setMeals] = useState<Toggle>("off");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation>(null);

  const selected = useMemo(() => programs.find((program) => program.id === selectedId) ?? null, [programs, selectedId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await apiRequest<LibraryPageData>("/api/v1/library/programs?limit=100");
      const eligiblePrograms = page.items.filter((program) => program.can_calendarize);
      setPrograms(eligiblePrograms);
      setSelectedId((current) => current && eligiblePrograms.some((program) => program.id === current) ? current : eligiblePrograms[0]?.id ?? null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  useFocusEffect(useCallback(() => { if (status === "authenticated") void load(); }, [load, status]));

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Buscando tus programas…" />;

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
    <Screen>
      <AppHeader eyebrow="Nuevo recorrido" title="Calendarizar programa" />
      {error ? <RecoverableErrorState message={error} onRetry={() => void load()} /> : null}
      {!programs.length ? (
        <EmptyState actionLabel="Ir a mis programas" message="Guarda primero un programa semanal para poder calendarizarlo." onAction={() => router.replace("/libraries/programs")} title="No hay programas disponibles" />
      ) : (
        <>
          <SectionTitle detail={`${programs.length} disponibles`} title="1. Elige un programa" />
          <View style={styles.programs}>
            {programs.map((program) => {
              const selectedProgram = program.id === selectedId;
              const weekIndicator = program.indicators.find((indicator) => indicator.label === "semanas");
              const dayIndicator = program.indicators.find((indicator) => indicator.label === "días con plan");
              return (
                <Pressable accessibilityLabel={`Programa ${program.name}`} accessibilityRole="radio" accessibilityState={{ selected: selectedProgram }} key={program.id} onPress={() => { setSelectedId(program.id); setConfirmation(null); }} style={({ pressed }) => [styles.programChoice, selectedProgram && styles.programSelected, pressed && styles.pressed]}>
                  <View style={styles.programCopy}><Text style={styles.programName}>{program.name}</Text><Text style={textStyles.caption}>{weekIndicator?.value ?? 1} semanas · {dayIndicator?.value ?? 0} días con plan</Text></View>
                  {selectedProgram ? <Pill color={tokens.color.program} label="Elegido" /> : null}
                </Pressable>
              );
            })}
          </View>

          <SectionTitle title="2. Define el comienzo" />
          <Card accent={tokens.color.program}>
            <Text style={textStyles.strong}>{selected?.name}</Text>
            <Field keyboardType="numbers-and-punctuation" label="Fecha de inicio (AAAA-MM-DD)" onChangeText={(value) => { setStartDate(value); setConfirmation(null); }} placeholder="2026-08-13" value={startDate} />
            <Field label="Zona horaria IANA" onChangeText={setTimezoneName} placeholder="America/Santiago" value={timezoneName} />
          </Card>

          <SectionTitle title="3. Prepara los avisos" />
          <Card muted>
            <Field keyboardType="numbers-and-punctuation" label="Hora del aviso diario" onChangeText={setDailyTime} placeholder="07:00" value={dailyTime} />
            <ChoiceRow<Toggle> label="Aviso del plan diario" onChange={setDaily} options={toggleOptions} value={daily} />
            <ChoiceRow<Toggle> label="Avisos según la hora de cada comida" onChange={setMeals} options={toggleOptions} value={meals} />
          </Card>

          {confirmation ? (
            <ConfirmationState busy={saving} confirmLabel={confirmation.kind === "replacement" ? "Cambiar programa" : "Continuar igualmente"} danger={confirmation.kind === "replacement"} message={confirmation.message} onCancel={() => setConfirmation(null)} onConfirm={() => void activate(confirmation.kind === "incomplete" ? { confirm_incomplete: true } : { replace_current: true })} title={confirmation.kind === "replacement" ? "¿Reemplazar tu programa actual?" : "Este programa está incompleto"} />
          ) : <Button disabled={!selectedId} label="Comenzar recorrido" loading={saving} onPress={() => void activate()} />}
          <Button label="Cancelar" onPress={() => router.back()} variant="secondary" />
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.65 },
  programChoice: { alignItems: "center", backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", padding: tokens.card.outerPadding },
  programCopy: { flex: 1, gap: 4 },
  programName: { color: tokens.color.textMain, fontSize: 17, fontWeight: "800" },
  programSelected: { borderColor: tokens.color.program, borderWidth: 2 },
  programs: { gap: tokens.spacing.sm },
});
