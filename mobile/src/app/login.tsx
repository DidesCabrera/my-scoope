import { type Href, Redirect, useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, View } from "react-native";

import { useSession } from "@/auth/session-context";
import { Brand, Button, Card, InlineNotice, Screen, textStyles } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { internalHref } from "@/navigation/internal-href";

export default function LoginScreen() {
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const returnHref = internalHref(returnTo);
  const { status, profile, authBusy, authError, authReady, startSignIn } = useSession();

  if (status === "authenticated") {
    if (profile?.review_disclosure_required) return <Redirect href={{ pathname: "/disclosures", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    if (!profile?.onboarding_completed) return <Redirect href={{ pathname: "/onboarding", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    return <Redirect href={returnHref ?? ("/today" as Href)} />;
  }

  return (
    <Screen contentStyle={styles.screen}>
      <Brand />
      <View style={styles.hero}>
        <Text style={styles.kicker}>NUTRICIÓN DE EJECUCIÓN</Text>
        <Text style={styles.heroTitle}>Tu cambio físico se construye hoy.</Text>
        <Text style={textStyles.muted}>Sigue tu programa, pesa tu comida y registra lo que realmente ocurre.</Text>
      </View>
      <Card accent={tokens.color.program}>
        <Text style={styles.cardTitle}>Continúa con tu cuenta</Text>
        <Text style={textStyles.muted}>Abriremos una ventana segura de My Scoope. PKCE protege el intercambio y tus tokens quedan cifrados en el dispositivo.</Text>
        {authError ? <InlineNotice tone="error">{authError}</InlineNotice> : null}
        <Button
          disabled={!authReady}
          label="Iniciar sesión o crear cuenta"
          loading={authBusy}
          onPress={() => void startSignIn(returnHref)}
        />
      </Card>
      <Text style={styles.footnote}>Precisión sin ruido. Tus decisiones nutricionales siguen siendo tuyas.</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { justifyContent: "space-between", paddingBottom: 30 },
  hero: { gap: 13, marginTop: 36 },
  kicker: { color: tokens.color.program, fontSize: 12, fontWeight: "900", letterSpacing: 1.6 },
  heroTitle: { color: tokens.color.textMain, fontSize: tokens.type.hero, fontWeight: "900", letterSpacing: -1.2, lineHeight: 39 },
  cardTitle: { color: tokens.color.textMain, fontSize: 20, fontWeight: "800" },
  footnote: { color: tokens.color.textSoft, fontSize: 12, lineHeight: 18, textAlign: "center" },
});
