import { Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { CalendarizationStatus, ReminderSettings, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, ChoiceRow, Field, InlineNotice, LoadingState, NativeDateTimeField, Screen, SectionTitle, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { NativeReminderState, syncNativeRemindersForProgram } from "@/notifications/native-reminders";
import { activateReminderPermission } from "@/notifications/reminder-permissions";

type Toggle = "on" | "off";
const toggleOptions: { value: Toggle; label: string }[] = [
  { value: "on", label: "Sí" },
  { value: "off", label: "No" },
];

export default function RemindersScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [settings, setSettings] = useState<ReminderSettings | null>(null);
  const [calendarizationStatus, setCalendarizationStatus] = useState<CalendarizationStatus | null>(null);
  const [timezoneName, setTimezoneName] = useState("");
  const [dailyTime, setDailyTime] = useState("");
  const [daily, setDaily] = useState<Toggle>("on");
  const [meals, setMeals] = useState<Toggle>("off");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nativeState, setNativeState] = useState<NativeReminderState | null>(null);
  const [syncingNative, setSyncingNative] = useState(false);
  const currentAgenda = useRef({ settings, calendarizationStatus });
  useEffect(() => { currentAgenda.current = { settings, calendarizationStatus }; }, [settings, calendarizationStatus]);

  const syncNative = useCallback(async (next: ReminderSettings | null, nextStatus: CalendarizationStatus | null, requestPermission = false) => {
    setSyncingNative(true);
    try {
      setNativeState(await syncNativeRemindersForProgram(next, nextStatus, apiRequest, { requestPermission }));
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSyncingNative(false);
    }
  }, [apiRequest]);

  useEffect(() => {
    void apiRequest<TodayData>("/api/v1/today")
      .then((today) => {
        const next = today.reminders;
        const nextStatus = today.calendarization?.status ?? null;
        setSettings(next);
        setCalendarizationStatus(nextStatus);
        if (next) {
          setTimezoneName(next.timezone_name);
          setDailyTime(next.daily_notification_time.slice(0, 5));
          setDaily(next.daily_notifications_enabled ? "on" : "off");
          setMeals(next.meal_notifications_enabled ? "on" : "off");
        }
      })
      .catch((nextError) => setError(userFacingError(nextError)))
      .finally(() => setLoading(false));
  }, [apiRequest, syncNative]);

  useFocusEffect(useCallback(() => {
    if (loading) return;
    const synchronize = () => {
      const agenda = currentAgenda.current;
      void syncNative(agenda.settings, agenda.calendarizationStatus);
    };
    synchronize();
    let previous = AppState.currentState;
    const listener = AppState.addEventListener("change", (next) => {
      if (next === "active" && previous !== "active") synchronize();
      previous = next;
    });
    return () => listener.remove();
  }, [loading, syncNative]));

  const activate = async () => {
    if (!nativeState || syncingNative) return;
    setError(null);
    try {
      await activateReminderPermission(nativeState.permission, {
        openSettings: () => Linking.openSettings(),
        synchronize: (requestPermission) => syncNative(settings, calendarizationStatus, requestPermission),
      });
    } catch { setError("No pudimos abrir los Ajustes. Puedes activar los avisos de My Scoope desde Ajustes de iOS."); }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando tu agenda…" />;

  async function save() {
    if (!settings) return;
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(dailyTime)) {
      setError("Usa una hora válida en formato HH:MM.");
      return;
    }
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await apiRequest<ReminderSettings>("/api/v1/program/active/reminders", {
        method: "PUT",
        body: JSON.stringify({
          timezone_name: timezoneName,
          daily_notification_time: dailyTime,
          daily_notifications_enabled: daily === "on",
          meal_notifications_enabled: meals === "on",
        }),
      });
      setSettings(updated);
      await syncNative(updated, calendarizationStatus);
      setSaved(true);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Programa vivido" title="Agenda de recordatorios" />
      <InlineNotice>Configura los avisos de My Scoope en este iPhone y el horario de los recordatorios de tu programa activo.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {saved ? <InlineNotice>Agenda actualizada y eventos futuros recalculados.</InlineNotice> : null}
      <Card accent={tokens.color.meal}>
        <View style={styles.nativeDelivery}>
          <View style={styles.nativeCopy}>
            <Text style={styles.eventTitle}>Avisos de iPhone</Text>
            <Text style={textStyles.caption}>{nativeDeliveryLabel(nativeState)}</Text>
          </View>
          <Button
            disabled={!nativeState || nativeState.permission === "unavailable"}
            label={nativeState?.permission === "denied" ? "Abrir Ajustes" : nativeState?.permission === "granted" ? "Sincronizar" : "Activar"}
            loading={syncingNative}
            onPress={() => void activate()}
            variant="secondary"
          />
        </View>
      </Card>
      {settings ? (
        <>
          <Card accent={tokens.color.meal}>
            <Field label="Zona horaria IANA" onChangeText={setTimezoneName} placeholder="America/Santiago" value={timezoneName} />
            <NativeDateTimeField label="Aviso del plan diario" minuteInterval={5} mode="time" onChange={setDailyTime} value={dailyTime} />
            <ChoiceRow<Toggle> label="Recordatorio diario" onChange={setDaily} options={toggleOptions} value={daily} />
            <ChoiceRow<Toggle> label="Recordatorios según hora de cada comida" onChange={setMeals} options={toggleOptions} value={meals} />
            <Button label="Guardar agenda" loading={saving} onPress={() => void save()} />
          </Card>
          <SectionTitle detail={`${settings.upcoming.length} próximos`} title="Eventos coordinados" />
          <Card muted>
            {settings.upcoming.length ? settings.upcoming.slice(0, 8).map((event, index) => (
              <View key={`${event.event_type}-${event.local_date}-${event.meal_key}-${index}`} style={styles.event}>
                <View>
                  <Text style={styles.eventTitle}>{event.event_type === "daily_plan" ? "Plan diario" : "Comida"}</Text>
                  <Text style={textStyles.caption}>{event.local_date} · {event.local_time.slice(0, 5)}</Text>
                </View>
                <Text style={styles.eventStatus}>{event.status}</Text>
              </View>
            )) : <Text style={textStyles.muted}>No hay eventos futuros pendientes con esta configuración.</Text>}
          </Card>
        </>
      ) : (
        <Card>
          <Text style={textStyles.muted}>Puedes activar los avisos ahora. Para recibir recordatorios de comidas y planes diarios, activa y calendariza un programa.</Text>
          <Button label="Ver calendario" onPress={() => router.push("/calendar")} variant="secondary" />
        </Card>
      )}
      <Button label="Volver a Today" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  nativeDelivery: { alignItems: "center", flexDirection: "row", gap: 12, justifyContent: "space-between" },
  nativeCopy: { flex: 1, gap: 4 },
  event: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", paddingVertical: 10 },
  eventTitle: { color: tokens.color.textMain, fontSize: 15, fontWeight: "800" },
  eventStatus: { color: tokens.color.textSoft, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
});

function nativeDeliveryLabel(state: NativeReminderState | null): string {
  if (!state) return "Comprobando permisos y agenda…";
  if (state.permission === "unavailable") return "Disponible en la app para iPhone.";
  if (state.permission === "denied") return "Desactivados en Ajustes de iOS.";
  if (state.permission === "undetermined") return "Aún no has decidido si permites avisos.";
  if (state.deliveryMode === "apns") return "Avisos activados para este dispositivo.";
  if (state.deliveryMode === "none") return "No hay avisos activos para el estado actual del programa.";
  return `${state.scheduledCount} avisos locales sincronizados.`;
}
