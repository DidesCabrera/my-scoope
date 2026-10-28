import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { Button, InlineNotice, MacroLoadingIndicator, Screen } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";

export default function ConfirmEmailScreen() {
  const { key } = useLocalSearchParams<{ key?: string }>();
  const router = useRouter();
  const { finishEmailConfirmation } = useSession();
  const started = useRef(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!key || started.current) return;
    started.current = true;
    void (async () => {
      try {
        const response = await fetch(`${appConfig.apiBaseUrl}/api/v1/auth/confirm-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ key }),
        });
        if (!response.ok) throw new Error("email_confirmation_failed");
        finishEmailConfirmation();
        router.replace("/login?emailConfirmed=1");
      } catch {
        setFailed(true);
      }
    })();
  }, [finishEmailConfirmation, key, router]);

  return (
    <Screen scroll={false} contentStyle={styles.content} headerMode="preserve">
      {failed || !key ? (
        <View style={styles.recovery}>
          <InlineNotice tone="warning">No pudimos confirmar este enlace. Puede haber vencido o ya haber sido utilizado.</InlineNotice>
          <Button label="Ir a iniciar sesión" onPress={() => router.replace("/login")} variant="secondary" />
        </View>
      ) : (
        <MacroLoadingIndicator accessibilityLabel="Confirmando tu correo" />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, justifyContent: "center" },
  recovery: { gap: tokens.spacing.md, width: "100%" },
});
