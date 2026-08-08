import { ResponseType, useAuthRequest } from "expo-auth-session";
import { Redirect } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import { useSession } from "@/auth/session-context";
import { Brand, Button, Card, InlineNotice, Screen, textStyles } from "@/components/ui/primitives";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";

WebBrowser.maybeCompleteAuthSession();

const discovery = {
  authorizationEndpoint: appConfig.oauthAuthorizationEndpoint,
  tokenEndpoint: appConfig.oauthTokenEndpoint,
};

export default function LoginScreen() {
  const { status, profile, completeAuthorizationCode } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const handledCode = useRef<string | null>(null);
  const [request, response, promptAsync] = useAuthRequest(
    {
      clientId: appConfig.oauthClientId,
      redirectUri: appConfig.oauthRedirectUri,
      responseType: ResponseType.Code,
      scopes: [...appConfig.mobileScopes],
      usePKCE: true,
    },
    discovery,
  );

  useEffect(() => {
    if (response?.type !== "success" || !request?.codeVerifier) return;
    const code = response.params.code;
    if (!code || handledCode.current === code) return;
    handledCode.current = code;
    setBusy(true);
    setError(null);
    void completeAuthorizationCode(code, request.codeVerifier)
      .catch((nextError) => setError(userFacingError(nextError)))
      .finally(() => setBusy(false));
  }, [completeAuthorizationCode, request?.codeVerifier, response]);

  if (status === "authenticated") {
    if (profile?.review_disclosure_required) return <Redirect href="./disclosures" />;
    return <Redirect href={profile?.onboarding_completed ? "/today" : "/onboarding"} />;
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
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button
          disabled={!request}
          label="Iniciar sesión o crear cuenta"
          loading={busy}
          onPress={() => {
            setError(null);
            void promptAsync().catch((nextError) => setError(userFacingError(nextError)));
          }}
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
