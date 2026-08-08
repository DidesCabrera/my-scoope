import { Redirect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { Alert, Text } from "react-native";
import { useState } from "react";

import { userFacingError } from "@/api/errors";
import type { AccountDeletionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, Field, InlineNotice, Screen, SectionTitle, textStyles } from "@/components/ui/primitives";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";

const supportEmail = "bacardides@gmail.com";

export default function AccountScreen() {
  const router = useRouter();
  const { status, session, apiRequest, signOut } = useSession();
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "anonymous") return <Redirect href="/login" />;

  async function deleteAccount() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<AccountDeletionData>("/api/v1/account/delete", {
        method: "POST",
        body: JSON.stringify({ confirmation, password }),
      });
      await signOut();
      Alert.alert("Cuenta eliminada", `Tu acceso fue revocado. Comprobante: ${result.receipt_id}`);
      router.replace("/login");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Tu cuenta" title={session?.display_name || session?.username || "My Scoope"} />
      <Card muted>
        <SectionTitle title="Privacidad y ayuda" />
        <Text style={textStyles.muted}>Consulta cómo tratamos tus datos, los términos del servicio o solicita ayuda.</Text>
        <Button label="Política de privacidad" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/privacy/`)} variant="secondary" />
        <Button label="Términos de uso" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/terms/`)} variant="secondary" />
        <Button label="Centro de soporte" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/support/`)} variant="secondary" />
        <Button label="Reportar contenido o un problema" onPress={() => void Linking.openURL(`mailto:${supportEmail}?subject=Reporte%20desde%20My%20Scoope`)} variant="secondary" />
      </Card>
      <InlineNotice tone="warning">My Scoope no reemplaza atención médica. Revisa cualquier cálculo, lectura OCR o propuesta asistida por IA antes de aplicarla.</InlineNotice>
      <Card accent={tokens.color.danger}>
        <SectionTitle title="Eliminar mi cuenta" />
        <Text style={textStyles.muted}>Esta acción revoca el acceso inmediatamente y elimina o anonimiza tus datos conforme a nuestra política. No se puede deshacer.</Text>
        <Field autoCapitalize="characters" label="Escribe ELIMINAR para confirmar" onChangeText={setConfirmation} value={confirmation} />
        <Field label="Contraseña (si tu cuenta usa una)" onChangeText={setPassword} secureTextEntry value={password} />
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={confirmation !== "ELIMINAR"} label="Eliminar cuenta definitivamente" loading={busy} onPress={deleteAccount} variant="danger" />
      </Card>
      <Button label="Volver a hoy" onPress={() => router.back()} variant="secondary" />
    </Screen>
  );
}
