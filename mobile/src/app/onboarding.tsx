import { type Href, Redirect, useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { StyleSheet } from "react-native";

import { userFacingError } from "@/api/errors";
import type { OnboardingAnalyzeInput, OnboardingStateData, ProposalDetail } from "@/api/types";
import { useSession } from "@/auth/session-context";
import {
  OnboardingJourneyView,
  onboardingJourneySteps,
  presentationPropsForOnboardingStep,
  type OnboardingJourneyController,
  type OnboardingJourneyStep,
  type OnboardingJourneyValues,
} from "@/components/onboarding";
import { LoadingState, Screen } from "@/components/ui";
import { internalHref } from "@/navigation/internal-href";

const introSteps: OnboardingJourneyStep[] = ["value", "structure", "panels", "control", "progress"];
const profileSteps: OnboardingJourneyStep[] = ["goal", "identity", "measurements", "activity", "dietary", "summary"];

const initialValues: OnboardingJourneyValues = {
  goal: "fat_loss",
  birthDate: "",
  sex: "male",
  height: "",
  weight: "",
  activityLevel: "light",
  trainingFrequency: 3,
  dietaryPattern: "omnivore",
  allergy: "",
  allergyDetails: "",
  avoidedFoods: "",
};

const allergyChoices = new Set(["gluten", "lácteos", "frutos secos", "mariscos"]);

function stepForState(state: OnboardingStateData): OnboardingJourneyStep {
  if (state.stage === "summary") return "summary";
  if (state.stage === "plan") return "dailyPlan";
  if (state.stage === "plans") return "plans";
  if (state.stage === "profile") return "goal";
  return "value";
}

function valuesForState(state: OnboardingStateData): OnboardingJourneyValues {
  const selectedAllergy = state.allergies_or_intolerances.find((item) => allergyChoices.has(item)) || "";
  return {
    goal: state.goal || initialValues.goal,
    birthDate: state.birth_date || "",
    sex: state.sex === "female" ? "female" : "male",
    height: state.height_cm ? String(state.height_cm) : "",
    weight: state.weight_kg ? String(state.weight_kg).replace(".", ",") : "",
    activityLevel: state.activity_level || initialValues.activityLevel,
    trainingFrequency: state.training_frequency ?? initialValues.trainingFrequency,
    dietaryPattern: state.dietary_pattern || initialValues.dietaryPattern,
    allergy: selectedAllergy,
    allergyDetails: state.allergies_or_intolerances.filter((item) => item !== selectedAllergy).join(", "),
    avoidedFoods: state.avoided_foods.join(", "),
  };
}

export default function OnboardingScreen() {
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const returnHref = internalHref(returnTo);
  const router = useRouter();
  const { status, profile, apiRequest } = useSession();
  const [step, setStep] = useState<OnboardingJourneyStep>("value");
  const [values, setValues] = useState<OnboardingJourneyValues>(initialValues);
  const [state, setState] = useState<OnboardingStateData | null>(null);
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (status !== "authenticated") return;
    setLoading(true);
    setError(null);
    try {
      const nextState = await apiRequest<OnboardingStateData>("/api/v1/onboarding/state");
      setState(nextState);
      setValues(valuesForState(nextState));
      setStep(stepForState(nextState));
      if (nextState.proposal_id) {
        setProposal(await apiRequest<ProposalDetail>(`/api/v1/proposals/${nextState.proposal_id}`));
      }
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setLoading(false);
    }
  }, [apiRequest, status]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  if (status === "anonymous") return <Redirect href={{ pathname: "/login", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
  if (profile?.onboarding_completed) return <Redirect href={returnHref ?? ("/today" as Href)} />;
  if (loading) return <LoadingState label="Preparando tu punto de partida…" />;
  if (step === "plans") {
    return <Redirect href={{ pathname: "/subscription", params: { origin: "onboarding", ...(returnHref ? { returnTo: String(returnHref) } : {}) } }} />;
  }
  if (profile?.review_disclosure_required && state && state.stage !== "intro") {
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
        const nextProposal = await apiRequest<ProposalDetail>("/api/v1/onboarding/generate-plan", { method: "POST" });
        setProposal(nextProposal);
        setStep("dailyPlan");
        return;
      }
      if (step === "dailyPlan") {
        const applied = await apiRequest<ProposalDetail>("/api/v1/onboarding/accept-plan", { method: "POST" });
        setProposal(applied);
        router.replace({ pathname: "/subscription", params: { origin: "onboarding", ...(returnHref ? { returnTo: String(returnHref) } : {}) } });
      }
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
    proposal,
    busy,
    error,
    onChange: updateValue,
    onNext: () => void next(),
    onBack: back,
    onAdjust: () => setStep("goal"),
  };

  const stepIndex = onboardingJourneySteps.findIndex((item) => item.key === step);
  const usesFixedDisclosuresFooter = stepIndex === 6;
  const usesFixedProfileChrome = stepIndex >= 7 && stepIndex <= 12;
  const presentationProps = presentationPropsForOnboardingStep(step);

  return (
    <Screen contentStyle={styles.screen} scroll={usesFixedDisclosuresFooter || usesFixedProfileChrome ? false : stepIndex >= 6 ? "auto" : false}>
      <OnboardingJourneyView controller={controller} {...presentationProps} step={step} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 },
});
