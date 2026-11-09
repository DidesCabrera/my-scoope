import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import { CalendarDays } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingCalendarization, OnboardingStateData, ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalDailyPlanCard } from "@/components/proposals/proposal-preview";
import { Button, Card, InlineNotice, LoadingState, Screen } from "@/components/ui";
import { Field } from "@/components/ui/primitives";
import { tokens } from "@/design/tokens";

type Minutas = { items: ProposalDetail[] };
const dietaryOptions = [
  ["omnivore", "Omnívora"],
  ["vegetarian", "Vegetariana"],
  ["vegan", "Vegana"],
  ["pescatarian", "Pescetariana"],
  ["flexitarian", "Flexitariana"],
] as const;

function splitPreferences(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export default function FirstMinutasScreen() {
  const router = useRouter();
  const { apiRequest, profile, status } = useSession();
  const setHeaderPresentation = useHeaderPresentation();
  const [state, setState] = useState<OnboardingStateData | null>(null);
  const [proposals, setProposals] = useState<ProposalDetail[]>([]);
  const [calendarization, setCalendarization] = useState<OnboardingCalendarization | null>(null);
  const [dietaryPattern, setDietaryPattern] = useState("omnivore");
  const [allergies, setAllergies] = useState("");
  const [avoidedFoods, setAvoidedFoods] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (status !== "authenticated") return;
    setError(null);
    try {
      const nextState = await apiRequest<OnboardingStateData>("/api/v1/onboarding/state", { cache: "no-store" });
      setState(nextState);
      setDietaryPattern(nextState.dietary_pattern || "omnivore");
      setAllergies(nextState.allergies_or_intolerances.join(", "));
      setAvoidedFoods(nextState.avoided_foods.join(", "));
      const ids = nextState.proposal_ids;
      setProposals(await Promise.all(ids.map((id) => apiRequest<ProposalDetail>(`/api/v1/proposals/${id}`))));
      setCalendarization(ids.length === 2
        ? await apiRequest<OnboardingCalendarization>("/api/v1/onboarding/calendarized-foods", { cache: "no-store" }) : null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, status]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));
  useFocusEffect(useCallback(() => {
    setHeaderPresentation({ fallback: "/today", mode: "back", title: "Tus primeras minutas" });
    return () => setHeaderPresentation({ mode: "default" });
  }, [setHeaderPresentation]));

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest<OnboardingStateData>("/api/v1/personal-records/preferences", {
        method: "PATCH",
        body: JSON.stringify({ dietary_pattern: dietaryPattern, allergies_or_intolerances: splitPreferences(allergies), avoided_foods: splitPreferences(avoidedFoods) }),
      });
      const generated = await apiRequest<Minutas>("/api/v1/onboarding/generate-plan", { method: "POST" });
      setProposals(generated.items);
      setCalendarization({ plans: generated.items.map((item) => ({ proposal_id: item.id, dailyplan_id: null, dates: [], foods: [] })), days_count: 0, foods: [] });
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const saved = await apiRequest<Minutas>("/api/v1/onboarding/accept-plan", { method: "POST" });
      setProposals(saved.items);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  if (status === "anonymous") return <Redirect href="/login" />;
  if (profile && !profile.onboarding_completed) return <Redirect href="/onboarding" />;
  if (loading && !state) return <LoadingState label="Preparando tus primeras minutas…" />;
  if (!state) return <Screen headerMode="preserve">
    <InlineNotice tone="error">{error ?? "No pudimos cargar tus preferencias."}</InlineNotice>
    <Button label="Reintentar" onPress={() => void load()} />
    <Button label="Volver a Inicio" onPress={() => router.dismissTo("/today" as Href)} variant="secondary" />
  </Screen>;

  const saved = proposals.length === 2 && proposals.every((item) => item.status === "applied");
  const assigned = calendarization?.plans.filter((plan) => plan.dates.length > 0).length ?? 0;
  return <Screen headerMode="preserve">
    <View style={styles.intro}>
      <Text style={styles.eyebrow}>PRIMEROS PASOS · GRATIS</Text>
      <Text accessibilityRole="header" style={styles.title}>{proposals.length === 2 ? "Tus 2 minutas personalizadas" : "Crea 2 minutas según tus objetivos"}</Text>
      <Text style={styles.subtitle}>{proposals.length === 2
        ? saved ? "Ya están guardadas. Prográmalas en tu calendario cuando quieras." : "Revísalas, guárdalas y prográmalas en tu calendario cuando quieras."
        : "Cuéntanos tus preferencias para crear dos minutas según tu objetivo nutricional. Puedes volver a Inicio si prefieres hacerlo más tarde."}</Text>
    </View>
    {proposals.length !== 2 ? <Card style={styles.preferences}>
      <Text style={styles.sectionTitle}>Tipo de alimentación</Text>
      <View accessibilityRole="radiogroup" style={styles.options}>{dietaryOptions.map(([value, label]) =>
        <Pressable accessibilityRole="radio" accessibilityState={{ selected: dietaryPattern === value }} key={value} onPress={() => setDietaryPattern(value)} style={[styles.option, dietaryPattern === value && styles.optionSelected]}>
          <Text style={styles.optionLabel}>{label}</Text>
        </Pressable>)}</View>
      <Field autoCapitalize="sentences" label="Alergias o intolerancias (si tienes)" onChangeText={setAllergies} placeholder="Ej. maní, gluten" value={allergies} />
      <Field autoCapitalize="sentences" label="Alimentos que no consumes" onChangeText={setAvoidedFoods} placeholder="Ej. cilantro, aceitunas" value={avoidedFoods} />
      <Text style={styles.helper}>Separa varios alimentos o alergias con comas.</Text>
      <Button label="Generar mis 2 minutas gratis" loading={busy} onPress={() => void generate()} />
    </Card> : <>
      {proposals.map((item) => item.dailyplan ? <View key={item.id} style={styles.plan}>
        <ProposalDailyPlanCard dailyplan={item.dailyplan} />
        {saved && item.applied_result?.object_id ? <Button
          icon={<CalendarDays color={tokens.color.surfaceApp} size={17} />}
          label={calendarization?.plans.some((plan) => plan.proposal_id === item.id && plan.dates.length > 0) ? "Programar en otro día" : "Programar en calendario"}
          onPress={() => router.push({ pathname: "/calendar/select-plans", params: { origin: "detail", dailyPlanId: String(item.applied_result!.object_id), returnTo: "/first-minutas" } })}
        /> : null}
      </View> : null)}
      {!saved ? <Button label="Guardar mis 2 minutas gratis" loading={busy} onPress={() => void save()} /> : <InlineNotice tone="info">Tus dos minutas están guardadas. {assigned === 2 ? "Ya están programadas en el calendario." : "Puedes programarlas ahora o desde Mis minutas diarias más adelante."}</InlineNotice>}
    </>}
    {error ? <InlineNotice tone="error">{error} Puedes volver a Inicio y reintentarlo más tarde.</InlineNotice> : null}
    <Button label="Volver a Inicio" onPress={() => router.dismissTo("/today" as Href)} variant="secondary" />
  </Screen>;
}

const styles = StyleSheet.create({
  intro: { gap: tokens.spacing.sm },
  eyebrow: { color: tokens.color.dailyPlan, fontSize: 11, fontWeight: tokens.weight.bold, letterSpacing: 1 },
  title: { color: tokens.color.textMain, fontSize: 25, fontWeight: tokens.weight.extraBold, lineHeight: 30 },
  subtitle: { color: tokens.color.textSoft, fontSize: 15, lineHeight: 22 },
  preferences: { gap: tokens.spacing.lg },
  sectionTitle: { color: tokens.color.textMain, fontSize: 17, fontWeight: tokens.weight.bold },
  options: { flexDirection: "row", flexWrap: "wrap", gap: tokens.spacing.sm },
  option: { borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm },
  optionSelected: { backgroundColor: tokens.color.surfaceElevated, borderColor: tokens.color.dailyPlan },
  optionLabel: { color: tokens.color.textMain, fontSize: 13, fontWeight: tokens.weight.semibold },
  helper: { color: tokens.color.textSoft, fontSize: 12 },
  plan: { gap: tokens.spacing.sm },
});
