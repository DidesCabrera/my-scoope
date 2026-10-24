import { Redirect, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import type { CalendarCommitmentKind } from "@/api/calendar-types";
import { useSession } from "@/auth/session-context";
import { commitmentKinds, commitmentPresentation } from "@/components/calendarization/calendar-commitments";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { InlineNotice, LoadingState, Screen, SystemSwitch } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { defaultCommitmentReminderSettings, loadCommitmentReminderSettings, saveCommitmentReminderSettings, syncCommitmentReminders, type CommitmentReminderSettings } from "@/notifications/commitment-reminders";

const descriptions: Record<CalendarCommitmentKind, string> = {
  shopping: "Avisarme cuando tenga compras programadas.",
  cooking: "Avisarme cuando tenga que cocinar.",
  training: "Avisarme cuando tenga un entrenamiento.",
  nutritionist: "Avisarme cuando tenga una cita nutricional.",
};

export default function CommitmentNotificationsScreen() {
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [settings, setSettings] = useState<CommitmentReminderSettings>(defaultCommitmentReminderSettings);
  const [loading, setLoading] = useState(true);
  const [savingKind, setSavingKind] = useState<CalendarCommitmentKind | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/calendar/registry", mode: "back", title: "Notificaciones de compromisos" });
    void loadCommitmentReminderSettings().then(setSettings).finally(() => setLoading(false));
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  async function toggle(kind: CalendarCommitmentKind, enabled: boolean) {
    const next = { ...settings, [kind]: enabled };
    setSettings(next); setSavingKind(kind); setError(null);
    try { await saveCommitmentReminderSettings(next); await syncCommitmentReminders(next, apiRequest); }
    catch { setSettings(settings); setError("No pudimos actualizar las notificaciones. Inténtalo nuevamente."); }
    finally { setSavingKind(null); }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (loading) return <LoadingState label="Cargando notificaciones…" />;

  return <Screen contentStyle={styles.content} headerMode="preserve">
    <Text accessibilityRole="header" style={styles.title}>Notificaciones de compromisos</Text>
    <Text style={styles.subtitle}>Elige qué compromisos quieres que My Scoope te recuerde.</Text>
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
    <View style={styles.list}>
      {commitmentKinds.map((kind) => {
        const presentation = commitmentPresentation[kind]; const Icon = presentation.icon;
        return <View key={kind} style={styles.row}>
          <Icon color={presentation.color} size={25} strokeWidth={2.1} />
          <View style={styles.copy}><Text style={styles.label}>{presentation.label}</Text><Text style={styles.description}>{descriptions[kind]}</Text></View>
          <SystemSwitch accessibilityLabel={`Notificaciones de ${presentation.label}`} disabled={savingKind !== null} onValueChange={(value) => void toggle(kind, value)} value={settings[kind]} />
        </View>;
      })}
    </View>
  </Screen>;
}

const styles = StyleSheet.create({
  content: { gap: tokens.spacing.lg },
  copy: { flex: 1, gap: tokens.spacing.xs },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  label: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold },
  list: { gap: 0 },
  row: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 82, paddingVertical: tokens.spacing.md },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: tokens.weight.semibold },
});
