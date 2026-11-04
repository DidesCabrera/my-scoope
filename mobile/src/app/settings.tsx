import { Redirect, useFocusEffect } from "expo-router";
import { Settings as SettingsIcon } from "lucide-react-native";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { useAssistantQuickChatPreferences } from "@/components/assistant/assistant-quick-chat-preferences";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Card, InlineNotice, LoadingState, Screen, SystemSwitch } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function SettingsScreen() {
  const { status } = useSession();
  const { ready, setShowFloatingButton, showFloatingButton } = useAssistantQuickChatPreferences();
  const setHeaderPresentation = useHeaderPresentation();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "default", title: "Settings" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  const toggleFloatingButton = async (value: boolean) => {
    setSaving(true);
    setError(null);
    try {
      await setShowFloatingButton(value);
    } catch {
      setError("No pudimos guardar esta preferencia. Inténtalo nuevamente.");
    } finally {
      setSaving(false);
    }
  };

  if (status === "anonymous") return <Redirect href="/login" />;
  if (!ready) return <LoadingState label="Cargando settings…" />;

  return (
    <Screen>
      <AppHeader eyebrow="Cuenta" eyebrowIcon={<SettingsIcon color={tokens.color.textSoft} size={20} />} title="Settings" />
      <Text style={styles.intro}>Personaliza cómo accedes a las funciones de My Scoope.</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <Card style={styles.card}>
        <View style={styles.row}>
          <View style={styles.copy}>
            <Text style={styles.label}>Mostrar botón flotante de asistente</Text>
            <Text style={styles.description}>Muestra un acceso movible para iniciar rápidamente una conversación.</Text>
          </View>
          <SystemSwitch
            accessibilityLabel="Mostrar botón flotante de asistente"
            disabled={saving}
            onValueChange={(value) => void toggleFloatingButton(value)}
            value={showFloatingButton}
          />
        </View>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { paddingVertical: tokens.spacing.xs },
  copy: { flex: 1, gap: tokens.spacing.xs },
  description: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 19 },
  intro: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 },
  label: { color: tokens.color.textMain, fontSize: 16, fontWeight: tokens.weight.semibold, lineHeight: 21 },
  row: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, minHeight: 76 },
});
