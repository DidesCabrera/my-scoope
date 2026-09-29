import { type Href, Redirect, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { Brand, Button, InlineNotice, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function OAuthCallbackScreen() {
  const router = useRouter();
  const { status, profile, authBusy, authReturnTo } = useSession();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), 20_000);
    return () => clearTimeout(timer);
  }, []);

  if (status === "authenticated") {
    if (profile?.review_disclosure_required) return <Redirect href={{ pathname: "/disclosures", params: authReturnTo ? { returnTo: String(authReturnTo) } : {} }} />;
    if (!profile?.onboarding_completed) return <Redirect href={{ pathname: "/onboarding", params: authReturnTo ? { returnTo: String(authReturnTo) } : {} }} />;
    return <Redirect href={authReturnTo ?? ("/today" as Href)} />;
  }
  if (status === "anonymous" && !authBusy) return <Redirect href="/login" />;

  return (
    <Screen scroll={false} contentStyle={styles.content} headerMode="preserve">
      <Brand />
      <ActivityIndicator color={tokens.color.interactivePrimary} size="large" />
      <Text style={styles.label}>Completando el inicio de sesión…</Text>
      {timedOut ? (
        <View style={styles.recovery}>
          <InlineNotice tone="warning">La conexión tardó demasiado. Puedes volver al inicio de sesión sin borrar tus datos.</InlineNotice>
          <Button label="Volver a iniciar sesión" onPress={() => router.replace("/login")} variant="secondary" />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { alignItems: "center", gap: tokens.spacing.lg, justifyContent: "center" },
  label: { color: tokens.color.textMuted, textAlign: "center" },
  recovery: { gap: tokens.spacing.md, width: "100%" },
});
