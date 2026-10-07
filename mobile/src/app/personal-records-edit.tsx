import { Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingStateData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Button, Card, ChoiceRow, Field, InlineNotice, NativeDateTimeField, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { localDateValue } from "@/presentation/date-time-values";

type Section = "body" | "metrics" | "planning" | "preferences";
const titles: Record<Section, string> = { body: "Ficha corporal", metrics: "Métricas corporales", planning: "Objetivo y actividad", preferences: "Preferencias alimentarias" };
const goalOptions = [["fat_loss", "Bajar grasa"], ["muscle_gain", "Ganar masa"], ["maintenance", "Mantención"], ["performance", "Rendimiento"], ["healthy_eating", "Comer mejor"]] as const;
const activityOptions = [["sedentary", "Sedentaria"], ["light", "Ligera"], ["moderate", "Moderada"], ["high", "Alta"], ["very_high", "Muy alta"]] as const;
const dietaryOptions = [["omnivore", "Omnívoro"], ["vegetarian", "Vegetariano"], ["vegan", "Vegano"], ["pescatarian", "Pescetariano"], ["flexitarian", "Flexitariano"]] as const;

export default function PersonalRecordsEditScreen() {
  const params = useLocalSearchParams<{ section?: string }>();
  const section = (["body", "metrics", "planning", "preferences"].includes(params.section ?? "") ? params.section : "body") as Section;
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [record, setRecord] = useState<OnboardingStateData | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/personal-records", mode: "back", title: titles[section] });
    return () => setHeaderPresentation({ mode: "default" });
  }, [section, setHeaderPresentation]));

  useEffect(() => {
    if (status !== "authenticated") return;
    void apiRequest<OnboardingStateData>("/api/v1/onboarding/state").then((next) => {
      setRecord(next);
      setValues({
        activity_level: next.activity_level, allergies_or_intolerances: next.allergies_or_intolerances.join(", "),
        avoided_foods: next.avoided_foods.join(", "), birth_date: next.birth_date ?? "", dietary_pattern: next.dietary_pattern,
        goal: next.goal, height_cm: next.height_cm?.toString() ?? "", sex: next.sex,
        training_frequency: next.training_frequency?.toString() ?? "", weight_kg: next.weight_kg?.toString() ?? "",
      });
    }).catch((nextError) => setError(userFacingError(nextError)));
  }, [apiRequest, status]);

  if (status === "anonymous") return <Redirect href="/login" />;
  const set = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }));

  async function save() {
    setBusy(true); setError(null);
    const split = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
    const payload = section === "body"
      ? { birth_date: values.birth_date, sex: values.sex, height_cm: Number(values.height_cm) }
      : section === "planning"
        ? { goal: values.goal, activity_level: values.activity_level, training_frequency: Number(values.training_frequency) }
        : section === "preferences"
          ? { dietary_pattern: values.dietary_pattern, allergies_or_intolerances: split(values.allergies_or_intolerances), avoided_foods: split(values.avoided_foods) }
          : { weight_kg: Number(values.weight_kg) };
    try {
      await apiRequest<OnboardingStateData>(`/api/v1/personal-records/${section}`, { body: JSON.stringify(payload), method: "PATCH" });
      router.replace("/personal-records");
    } catch (nextError) { setError(userFacingError(nextError)); } finally { setBusy(false); }
  }

  return (
    <Screen>
      <AppHeader eyebrow="Editar información" title={titles[section]} />
      <Card style={styles.form}>
        {!record ? <Text style={styles.loading}>Cargando información…</Text> : null}
        {section === "body" ? <>
          <NativeDateTimeField label="Fecha de nacimiento" maximumValue={localDateValue()} mode="date" onChange={(value) => set("birth_date", value)} value={values.birth_date ?? ""} />
          <ChoiceRow label="Sexo para cálculo nutricional" onChange={(value) => set("sex", value)} options={[{ label: "Femenino", value: "female" }, { label: "Masculino", value: "male" }]} value={values.sex ?? ""} />
          <Field keyboardType="number-pad" label="Altura en centímetros" onChangeText={(value) => set("height_cm", value)} value={values.height_cm ?? ""} />
        </> : null}
        {section === "planning" ? <>
          <OptionGrid label="Objetivo nutricional" onChange={(value) => set("goal", value)} options={goalOptions} value={values.goal} />
          <OptionGrid label="Actividad habitual" onChange={(value) => set("activity_level", value)} options={activityOptions} value={values.activity_level} />
          <Field keyboardType="number-pad" label="Entrenamientos por semana (0–7)" onChangeText={(value) => set("training_frequency", value)} value={values.training_frequency ?? ""} />
        </> : null}
        {section === "preferences" ? <>
          <OptionGrid label="Patrón alimentario" onChange={(value) => set("dietary_pattern", value)} options={dietaryOptions} value={values.dietary_pattern} />
          <Field label="Alergias o intolerancias, separadas por comas" onChangeText={(value) => set("allergies_or_intolerances", value)} value={values.allergies_or_intolerances ?? ""} />
          <Field label="Alimentos evitados, separados por comas" onChangeText={(value) => set("avoided_foods", value)} value={values.avoided_foods ?? ""} />
        </> : null}
        {section === "metrics" ? <Field keyboardType="decimal-pad" label="Peso actual en kg" onChangeText={(value) => set("weight_kg", value)} value={values.weight_kg ?? ""} /> : null}
        {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
        <Button disabled={!record} label="Guardar cambios" loading={busy} onPress={() => void save()} />
        <Button disabled={busy} label="Cancelar" onPress={() => router.back()} variant="secondary" />
      </Card>
    </Screen>
  );
}

function OptionGrid({ label, onChange, options, value }: { label: string; onChange(value: string): void; options: readonly (readonly [string, string])[]; value?: string }) {
  return <View style={styles.optionField}><Text style={styles.optionLabel}>{label}</Text><View style={styles.options}>{options.map(([key, text]) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: key === value }} key={key} onPress={() => onChange(key)} style={[styles.option, key === value && styles.optionSelected]}><Text style={[styles.optionText, key === value && styles.optionTextSelected]}>{text}</Text></Pressable>)}</View></View>;
}

const styles = StyleSheet.create({
  form: { gap: tokens.spacing.lg }, loading: { color: tokens.color.textMuted }, optionField: { gap: tokens.spacing.sm },
  optionLabel: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
  options: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  option: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  optionSelected: { backgroundColor: tokens.color.textMain, borderColor: tokens.color.textMain },
  optionText: { color: tokens.color.textMuted, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold },
  optionTextSelected: { color: tokens.color.surfaceApp },
});
