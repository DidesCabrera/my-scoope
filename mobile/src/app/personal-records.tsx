import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { Activity, Files, Salad, Scale, Target } from "lucide-react-native";
import { useCallback, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingStateData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { AppHeader, Button, Card, InlineNotice, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

type RecordRow = { label: string; value: string };

const goalLabels: Record<string, string> = {
  fat_loss: "Bajar grasa",
  healthy_eating: "Comer mejor",
  maintenance: "Mantención",
  muscle_gain: "Ganar masa muscular",
  performance: "Rendimiento deportivo",
};
const activityLabels: Record<string, string> = {
  high: "Alta",
  light: "Ligera",
  moderate: "Moderada",
  sedentary: "Sedentaria",
  very_high: "Muy alta",
};
const dietaryLabels: Record<string, string> = {
  omnivore: "Omnívoro",
  pescatarian: "Pescetariano",
  vegan: "Vegano",
  vegetarian: "Vegetariano",
};

function valueLabel(value: string | null | undefined, labels?: Record<string, string>) {
  if (!value) return "Sin completar";
  return labels?.[value] ?? value.replaceAll("_", " ");
}

function listLabel(values: string[]) {
  return values.length ? values.join(", ") : "Sin registrar";
}

export default function PersonalRecordsScreen() {
  const router = useRouter();
  const { apiRequest, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [state, setState] = useState<OnboardingStateData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ mode: "default", title: "Fichas personales" });
    if (status === "authenticated") {
      setError(null);
      void apiRequest<OnboardingStateData>("/api/v1/onboarding/state")
        .then(setState)
        .catch((nextError) => setError(userFacingError(nextError)));
    }
    return () => setHeaderPresentation({ mode: "default" });
  }, [apiRequest, setHeaderPresentation, status]));

  if (status === "anonymous") return <Redirect href="/login" />;

  const cards: { action?: { label: string; href: Href }; icon: typeof Files; rows: RecordRow[]; subtitle: string; title: string }[] = [
    {
      action: { href: "/personal-records-edit?section=body" as Href, label: "Editar información" },
      icon: Activity,
      rows: [
        { label: "Fecha de nacimiento", value: state?.birth_date ?? "Sin completar" },
        { label: "Sexo nutricional", value: valueLabel(state?.sex, { female: "Femenino", male: "Masculino" }) },
        { label: "Altura", value: state?.height_cm ? `${state.height_cm} cm` : "Sin completar" },
      ],
      subtitle: "Base estable para cálculos nutricionales.",
      title: "Ficha corporal",
    },
    {
      action: { href: "/personal-records-edit?section=planning" as Href, label: "Editar información" },
      icon: Target,
      rows: [
        { label: "Objetivo", value: valueLabel(state?.goal, goalLabels) },
        { label: "Actividad habitual", value: valueLabel(state?.activity_level, activityLabels) },
        { label: "Entrenamientos", value: state?.training_frequency != null ? `${state.training_frequency} por semana` : "Sin completar" },
      ],
      subtitle: "Contexto persistente para objetivos, planes y programas.",
      title: "Objetivo y actividad",
    },
    {
      action: { href: "/personal-records-edit?section=preferences" as Href, label: "Editar información" },
      icon: Salad,
      rows: [
        { label: "Patrón", value: valueLabel(state?.dietary_pattern, dietaryLabels) },
        { label: "Alergias o intolerancias", value: listLabel(state?.allergies_or_intolerances ?? []) },
        { label: "Alimentos evitados", value: listLabel(state?.avoided_foods ?? []) },
      ],
      subtitle: "Preferencias aprobadas y disponibles entre conversaciones.",
      title: "Preferencias alimentarias",
    },
    {
      action: { href: "/personal-records-edit?section=metrics" as Href, label: "Editar información" },
      icon: Scale,
      rows: [{ label: "Peso actual", value: state?.weight_kg != null ? `${state.weight_kg.toFixed(1)} kg` : "Sin registro" }],
      subtitle: "Medición corporal vigente para cálculos y seguimiento.",
      title: "Métricas corporales",
    },
  ];

  return (
    <Screen>
      <AppHeader eyebrow="Información personal" eyebrowIcon={<Files color={tokens.color.textSoft} size={20} />} title="Fichas personales" />
      <Text style={styles.intro}>La información que My Scoope usa para cálculos nutricionales, objetivos y construcción de planes, reunida en un solo lugar.</Text>
      {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
      {cards.map(({ action, icon: Icon, rows, subtitle, title }) => (
        <Card key={title} style={styles.card}>
          <View style={styles.cardHeading}>
            <View style={styles.icon}><Icon color={tokens.color.textMain} size={20} strokeWidth={2} /></View>
            <View style={styles.headingCopy}>
              <Text style={styles.title}>{title}</Text>
              <Text style={styles.subtitle}>{subtitle}</Text>
            </View>
          </View>
          <View>
            {rows.map((row, index) => (
              <View key={row.label} style={[styles.row, index === rows.length - 1 && styles.rowLast]}>
                <Text style={styles.label}>{row.label}</Text>
                <Text style={styles.value}>{row.value}</Text>
              </View>
            ))}
          </View>
          {action ? <Button label={action.label} onPress={() => router.push(action.href)} variant="secondary" /> : null}
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { gap: tokens.spacing.md },
  cardHeading: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.md },
  headingCopy: { flex: 1, gap: 3 },
  icon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 40, justifyContent: "center", width: 40 },
  intro: { color: tokens.color.textMuted, fontSize: tokens.type.body, lineHeight: 22 },
  label: { color: tokens.color.textMuted, flex: 1, fontSize: tokens.type.caption },
  row: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  rowLast: { borderBottomWidth: 0 },
  subtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 18 },
  title: { color: tokens.color.textMain, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  value: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.semibold, textAlign: "right" },
});
