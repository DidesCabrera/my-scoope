import { Redirect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { useState } from "react";
import { Text } from "react-native";

import { userFacingError } from "@/api/errors";
import type { ProfileData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Brand, Button, Card, InlineNotice, Screen, SectionTitle, textStyles } from "@/components/ui";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";

export default function DisclosuresScreen() {
  const router = useRouter();
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (status === "authenticated" && profile && !profile.review_disclosure_required) {
    return <Redirect href={profile.onboarding_completed ? "/today" : "/onboarding"} />;
  }

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<ProfileData>("/api/v1/account/disclosures", {
        method: "POST",
        body: JSON.stringify({ accepted: true }),
      });
      const nextProfile = await refreshProfile();
      router.replace(nextProfile.onboarding_completed ? "/today" : "/onboarding");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Brand />
      <AppHeader eyebrow="Antes de comenzar" title="Tu decisión sigue siendo la última" />
      <Text style={textStyles.muted}>My Scoope está hecho para personas que gestionan activamente su alimentación y quieren ejecutar un programa con disciplina.</Text>
      <Card accent={tokens.color.warning}>
        <SectionTitle title="No es atención médica" />
        <Text style={textStyles.body}>La app no diagnostica, trata ni reemplaza a un médico o nutricionista. Si tienes una condición médica, síntomas, embarazo o restricciones clínicas, consulta a un profesional.</Text>
      </Card>
      <Card accent={tokens.color.interactivePrimary}>
        <SectionTitle title="Revisa antes de aplicar" />
        <Text style={textStyles.body}>Los cálculos, lecturas de etiquetas y propuestas asistidas por IA pueden contener errores. Confirma cantidades, ingredientes y cambios antes de usarlos.</Text>
      </Card>
      <Card muted>
        <SectionTitle title="Privacidad y control" />
        <Text style={textStyles.muted}>Si digitalizas una etiqueta, una copia reducida y sin metadatos se envía temporalmente a OpenAI para extraer sus valores. My Scoope no guarda esa foto salvo que tú actives expresamente “Guardar copia procesada”; podrás verla y eliminarla después. Puedes revisar nuestra política y eliminar tu cuenta desde la app.</Text>
        <Button label="Leer política de privacidad" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/privacy/`)} variant="secondary" />
        <Button label="Leer términos de uso" onPress={() => void Linking.openURL(`${appConfig.apiBaseUrl}/terms/`)} variant="secondary" />
      </Card>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      <Button label="Entiendo y quiero continuar" loading={busy} onPress={accept} />
      <Text style={textStyles.caption}>Confirmación {profile?.review_disclosure_version ?? "cml08.v1"}</Text>
    </Screen>
  );
}
