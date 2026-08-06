import { Redirect, useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingInput, ProfileData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AppHeader, Button, Card, ChoiceRow, Field, InlineNotice, Screen, textStyles } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type Sex = "male" | "female";

export default function OnboardingScreen() {
  const router = useRouter();
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const [birthDate, setBirthDate] = useState("");
  const [sex, setSex] = useState<Sex>("male");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (profile?.onboarding_completed) return <Redirect href="/today" />;

  async function submit() {
    const payload: OnboardingInput = {
      birth_date: birthDate,
      sex,
      height_cm: Number(height),
      weight_kg: Number(weight.replace(",", ".")),
    };
    setBusy(true);
    setError(null);
    try {
      await apiRequest<ProfileData>("/api/v1/onboarding", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshProfile();
      router.replace("/today");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  const complete = /^\d{4}-\d{2}-\d{2}$/.test(birthDate) && Number(height) > 0 && Number(weight.replace(",", ".")) > 0;

  return (
    <Screen>
      <AppHeader eyebrow="Tu punto de partida" title="Construyamos tu ficha" />
      <Text style={textStyles.muted}>Estos datos permiten calcular y revisar planes para tu propio cuerpo. Podrás actualizarlos más adelante.</Text>
      <Card accent={tokens.color.dailyPlan}>
        <Text style={styles.step}>01 · PERFIL CORPORAL</Text>
        <Field label="Fecha de nacimiento" onChangeText={setBirthDate} placeholder="AAAA-MM-DD" value={birthDate} />
        <ChoiceRow<Sex>
          label="Sexo para cálculo nutricional"
          onChange={setSex}
          options={[
            { value: "male", label: "Masculino" },
            { value: "female", label: "Femenino" },
          ]}
          value={sex}
        />
        <View style={styles.measurements}>
          <View style={styles.measurement}>
            <Field keyboardType="number-pad" label="Altura (cm)" onChangeText={setHeight} placeholder="178" value={height} />
          </View>
          <View style={styles.measurement}>
            <Field keyboardType="decimal-pad" label="Peso actual (kg)" onChangeText={setWeight} placeholder="82.5" value={weight} />
          </View>
        </View>
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={!complete} label="Guardar y ver mi día" loading={busy} onPress={submit} />
      </Card>
      <InlineNotice>My Scoope apoya planificación y autogestión nutricional. No diagnostica ni reemplaza atención médica.</InlineNotice>
    </Screen>
  );
}

const styles = StyleSheet.create({
  step: { color: tokens.color.dailyPlan, fontSize: 12, fontWeight: "900", letterSpacing: 1.2 },
  measurements: { flexDirection: "row", gap: tokens.spacing.md },
  measurement: { flex: 1 },
});
