import { type Href, Redirect, Stack, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingAnalyzeInput, OnboardingCalendarization, OnboardingStateData, ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import {
  OnboardingJourneyView,
  onboardingScreenChromeForStep,
  presentationPropsForOnboardingStep,
  type OnboardingJourneyController,
  type OnboardingJourneyStep,
  type OnboardingJourneyValues,
} from "@/components/onboarding";
import { LoadingState, Screen } from "@/components/ui";
import { internalHref } from "@/navigation/internal-href";

const introSteps: OnboardingJourneyStep[] = ["value", "structure", "control", "panels", "panelsCopy", "compareShare", "progress"];
const profileSteps: OnboardingJourneyStep[] = ["goal", "identity", "measurements", "activity", "dietary", "summary"];

const initialValues: OnboardingJourneyValues = {
  goal: "fat_loss",
  birthDate: "2000-01-01",
  sex: "male",
  height: "180",
  weight: "80",
  activityLevel: "light",
  trainingFrequency: 3,
  dietaryPattern: "omnivore",
  allergy: "",
  allergyDetails: "",
  avoidedFoods: "",
};

const allergyChoices = new Set(["gluten", "lácteos", "frutos secos", "mariscos"]);
type OnboardingMinutas = { items: ProposalDetail[] };

function stepForState(state: OnboardingStateData): OnboardingJourneyStep {
  if (state.stage === "summary") return "summary";
  if (state.stage === "plan") return "dailyPlan";
  if (state.stage === "plans") return state.proposal_ids?.length === 2 ? "dailyPlan" : "plans";
  if (state.stage === "profile") return "goal";
  return "value";
}

function valuesForState(state: OnboardingStateData): OnboardingJourneyValues {
  const selectedAllergy = state.allergies_or_intolerances.find((item) => allergyChoices.has(item)) || "";
  return {
    goal: state.goal || initialValues.goal,
    birthDate: state.birth_date || initialValues.birthDate,
    sex: state.sex === "female" ? "female" : "male",
    height: state.height_cm ? String(state.height_cm) : initialValues.height,
    weight: state.weight_kg ? String(state.weight_kg).replace(".", ",") : initialValues.weight,
    activityLevel: state.activity_level || initialValues.activityLevel,
    trainingFrequency: state.training_frequency ?? initialValues.trainingFrequency,
    dietaryPattern: state.dietary_pattern || initialValues.dietaryPattern,
    allergy: selectedAllergy,
    allergyDetails: state.allergies_or_intolerances.filter((item) => item !== selectedAllergy).join(", "),
    avoidedFoods: state.avoided_foods.join(", "),
  };
}

export default function OnboardingScreen() {
  const { returnTo, reviewIntro } = useLocalSearchParams<{ returnTo?: string; reviewIntro?: string }>();
  const returnHref = internalHref(returnTo);
  const router = useRouter();
  const { status, profile, apiRequest, refreshProfile } = useSession();
  const disclosureRequired = Boolean(profile?.review_disclosure_required);
  const [step, setStep] = useState<OnboardingJourneyStep>("value");
  const [values, setValues] = useState<OnboardingJourneyValues>(initialValues);
  const [state, setState] = useState<OnboardingStateData | null>(null);
  const [proposals, setProposals] = useState<ProposalDetail[]>([]);
  const [calendarization, setCalendarization] = useState<OnboardingCalendarization | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (status !== "authenticated") return;
    setError(null);
    try {
      const nextState = await apiRequest<OnboardingStateData>("/api/v1/onboarding/state");
      setState(nextState);
      setValues(valuesForState(nextState));
      setStep(reviewIntro === "1" && disclosureRequired ? "progress" : stepForState(nextState));
      const proposalIds = nextState.proposal_ids?.length ? nextState.proposal_ids : nextState.proposal_id ? [nextState.proposal_id] : [];
      setProposals(await Promise.all(proposalIds.map((id) => apiRequest<ProposalDetail>(`/api/v1/proposals/${id}`))));
      setCalendarization(proposalIds.length === 2
        ? await apiRequest<OnboardingCalendarization>("/api/v1/onboarding/calendarized-foods") : null);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, disclosureRequired, reviewIntro, status]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  if (status === "anonymous") return <Redirect href={{ pathname: "/login", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
  if (profile?.onboarding_completed) return <Redirect href={returnHref ?? ("/today" as Href)} />;
  if (loading) return <LoadingState label="Preparando tu punto de partida…" />;
  if (step === "plans") {
    return <Redirect href={{ pathname: "/subscription", params: { origin: "onboarding", ...(returnHref ? { returnTo: String(returnHref) } : {}) } }} />;
  }
  if (profile?.review_disclosure_required && state && state.stage !== "intro" && !(reviewIntro === "1" && introSteps.includes(step))) {
    return <Redirect href={{ pathname: "/disclosures", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
  }

  const updateValue = (field: keyof OnboardingJourneyValues, value: string | number) => {
    setValues((current) => ({ ...current, [field]: value } as OnboardingJourneyValues));
    setError(null);
  };

  async function analyze() {
    const height = Number(values.height);
    const weight = Number(values.weight.replace(",", "."));
    if (!/^\d{4}-\d{2}-\d{2}$/.test(values.birthDate)) throw new Error("Ingresa la fecha con formato AAAA-MM-DD.");
    if (height < 80 || height > 250) throw new Error("La altura debe estar entre 80 y 250 cm.");
    if (weight < 25 || weight > 350) throw new Error("El peso debe estar entre 25 y 350 kg.");
    const allergyDetails = values.allergyDetails.split(",").map((item) => item.trim()).filter(Boolean);
    if (values.allergy === "otra" && allergyDetails.length === 0) {
      throw new Error("Describe la alergia o condición relevante antes de analizar.");
    }
    const payload: OnboardingAnalyzeInput = {
      birth_date: values.birthDate,
      sex: values.sex,
      height_cm: height,
      weight_kg: weight,
      goal: values.goal,
      activity_level: values.activityLevel,
      training_frequency: values.trainingFrequency,
      dietary_pattern: values.dietaryPattern,
      allergies_or_intolerances: [
        ...(values.allergy && values.allergy !== "otra" ? [values.allergy] : []),
        ...allergyDetails,
      ],
      avoided_foods: values.avoidedFoods.split(",").map((item) => item.trim()).filter(Boolean),
    };
    const nextState = await apiRequest<OnboardingStateData>("/api/v1/onboarding/analyze", { method: "POST", body: JSON.stringify(payload) });
    setState(nextState);
    setStep("summary");
  }

  async function next() {
    setBusy(true);
    setError(null);
    try {
      const introIndex = introSteps.indexOf(step);
      if (introIndex >= 0) {
        if (introIndex < introSteps.length - 1) setStep(introSteps[introIndex + 1]);
        else {
          await apiRequest<OnboardingStateData>("/api/v1/onboarding/intro-complete", { method: "POST" });
          if (profile?.review_disclosure_required) router.replace({ pathname: "/disclosures", params: returnHref ? { returnTo: String(returnHref) } : {} });
          else setStep("goal");
        }
        return;
      }
      const profileIndex = profileSteps.indexOf(step);
      if (profileIndex >= 0 && step !== "dietary" && step !== "summary") {
        if (step === "identity" && !/^\d{4}-\d{2}-\d{2}$/.test(values.birthDate)) {
          throw new Error("Ingresa la fecha con formato AAAA-MM-DD.");
        }
        if (step === "measurements") {
          const height = Number(values.height);
          const weight = Number(values.weight.replace(",", "."));
          if (height < 80 || height > 250) throw new Error("La altura debe estar entre 80 y 250 cm.");
          if (weight < 25 || weight > 350) throw new Error("El peso debe estar entre 25 y 350 kg.");
        }
        setStep(profileSteps[profileIndex + 1]);
        return;
      }
      if (step === "dietary") {
        await analyze();
        return;
      }
      if (step === "summary") {
        const generated = await apiRequest<OnboardingMinutas>("/api/v1/onboarding/generate-plan", { method: "POST" });
        setProposals(generated.items);
        setCalendarization({ plans: generated.items.map((item) => ({ proposal_id: item.id, dailyplan_id: null, dates: [], foods: [] })), days_count: 0, foods: [] });
        setStep("dailyPlan");
        return;
      }
      if (step === "dailyPlan") {
        if (proposals.length === 2 && calendarization?.plans.filter((plan) => plan.dates.length > 0).length !== 2) {
          throw new Error("Calendariza ambas minutas antes de continuar.");
        }
        const applied = await apiRequest<OnboardingMinutas>("/api/v1/onboarding/accept-plan", { method: "POST" });
        setProposals(applied.items);
        router.replace({ pathname: "/subscription", params: { origin: "onboarding", ...(returnHref ? { returnTo: String(returnHref) } : {}) } });
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function calendarize(proposalId: number) {
    setBusy(true);
    setError(null);
    try {
      const applied = proposals.every((item) => item.status === "applied")
        ? proposals
        : (await apiRequest<OnboardingMinutas>("/api/v1/onboarding/accept-plan", { method: "POST" })).items;
      setProposals(applied);
      const dailyPlanId = applied.find((item) => item.id === proposalId)?.applied_result?.object_id;
      if (!dailyPlanId) throw new Error("No pudimos abrir esta minuta en el calendario.");
      void refreshProfile().catch(() => undefined);
      router.push({ pathname: "/calendar/select-plans", params: { origin: "onboarding", dailyPlanId: String(dailyPlanId) } });
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  function back() {
    setError(null);
    const introIndex = introSteps.indexOf(step);
    if (introIndex > 0) return setStep(introSteps[introIndex - 1]);
    const profileIndex = profileSteps.indexOf(step);
    if (profileIndex > 0) return setStep(profileSteps[profileIndex - 1]);
    if (step === "goal") return setStep("progress");
    if (step === "dailyPlan") return setStep("summary");
    if (step === "plans") return setStep("dailyPlan");
  }

  const controller: OnboardingJourneyController = {
    values,
    estimate: state?.estimate,
    proposal: proposals[0] ?? null,
    proposals,
    calendarization,
    busy,
    error,
    onChange: updateValue,
    onNext: () => void next(),
    onCalendarize: (proposalId) => void calendarize(proposalId),
    onOpenMeal: (proposalId, mealIndex) => router.push(`/onboarding/minutas/${proposalId}/meals/${mealIndex}` as Href),
    onBack: back,
    onAdjust: () => setStep("goal"),
  };

  const { headerCompensationTop, scroll } = onboardingScreenChromeForStep(step);
  const presentationProps = presentationPropsForOnboardingStep(step);

  return (
    <>
      <Stack.Screen options={{ gestureEnabled: false, headerShown: false }} />
      <Screen contentStyle={[styles.screen, { paddingTop: headerCompensationTop }]} scroll={scroll}>
        <OnboardingJourneyView controller={controller} {...presentationProps} step={step} />
      </Screen>
    </>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 },
});
