import { Redirect, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ReminderSettings, TodayData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, ChoiceRow, Field, InlineNotice, LoadingState, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";
import { NativeReminderState, syncNativeReminders } from "@/notifications/native-reminders";

type Toggle = "on" | "off";
const toggleOptions: { value: Toggle; label: string }[] = [
  { value: "on", label: "Sí" },
  { value: "off", label: "No" },
];

export default function RemindersScreen() {
  const router = useRouter();
  const { status, apiRequest } = useSession();
  const [settings, setSettings] = useState<ReminderSettings | null>(null);
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

  const syncNative = useCallback(async (next: ReminderSettings, requestPermission = false) => {
    setSyncingNative(true);
    try {
      setNativeState(await syncNativeReminders(next, apiRequest, { requestPermission }));
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
        setSettings(next);
        if (next) {
          setTimezoneName(next.timezone_name);
          setDailyTime(next.daily_notification_time.slice(0, 5));
          setDaily(next.daily_notifications_enabled ? "on" : "off");
          setMeals(next.meal_notifications_enabled ? "on" : "off");
          void syncNative(next);
        }
      })
      .catch((nextError) => setError(userFacingError(nextError)))
      .finally(() => setLoading(false));
  }, [apiRequest, syncNative]);

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
      await syncNative(updated);
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
      <InlineNotice>La calendarización gobierna las horas y eventos. iOS usa APNs cuando el servidor está habilitado y conserva avisos locales como respaldo; nunca duplica ambos modos.</InlineNotice>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {saved ? <InlineNotice>Agenda actualizada y eventos futuros recalculados.</InlineNotice> : null}
      {settings ? (
        <>
          <Card accent={tokens.color.meal}>
            <View style={styles.nativeDelivery}>
              <View style={styles.nativeCopy}>
                <Text style={styles.eventTitle}>Avisos de iPhone</Text>
                <Text style={textStyles.caption}>{nativeDeliveryLabel(nativeState)}</Text>
              </View>
              <Button
                label={nativeState?.permission === "granted" ? "Sincronizar" : "Activar"}
                loading={syncingNative}
                onPress={() => void syncNative(settings, true)}
                variant="secondary"
              />
            </View>
            <Field label="Zona horaria IANA" onChangeText={setTimezoneName} placeholder="America/Santiago" value={timezoneName} />
            <Field keyboardType="numbers-and-punctuation" label="Aviso del plan diario" onChangeText={setDailyTime} placeholder="07:00" value={dailyTime} />
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
        <Card><Text style={textStyles.muted}>No hay una calendarización activa para configurar.</Text></Card>
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
  if (state.deliveryMode === "apns") return "APNs activo para este dispositivo.";
  return `${state.scheduledCount} avisos locales sincronizados.`;
}
