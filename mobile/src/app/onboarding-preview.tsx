import { type Href, Redirect, useRouter } from "expo-router";
import { useMemo, useState } from "react";

import { useSession } from "@/auth/session-context";
import {
  OnboardingJourneyView,
  type OnboardingJourneyController,
  type OnboardingJourneyStep,
  type OnboardingJourneyValues,
  onboardingJourneyPreviewValues,
  onboardingJourneySteps,
  topInsetReductionForOnboardingStoryboard,
} from "@/components/onboarding";
import { LoadingState, Screen } from "@/components/ui";

export default function OnboardingPreviewScreen() {
  const router = useRouter();
  const { session, status } = useSession();
  const [stepIndex, setStepIndex] = useState(0);
  const [values, setValues] = useState<OnboardingJourneyValues>({ ...onboardingJourneyPreviewValues });

  const step = onboardingJourneySteps[stepIndex]?.key ?? "login";
  const usesFixedDisclosuresFooter = stepIndex === 6;
  const usesFixedProfileChrome = stepIndex >= 7 && stepIndex <= 12;
  const storyboardTopInsetReduction = topInsetReductionForOnboardingStoryboard(step as OnboardingJourneyStep)
    + (stepIndex >= 1 && stepIndex <= 6 ? 20 : 0)
    + (stepIndex >= 6 ? 20 : 0)
    + (step === "plans" ? 20 : 0);
  const controller = useMemo<OnboardingJourneyController>(() => ({
    onAdjust: () => setStepIndex(onboardingJourneySteps.findIndex((item) => item.key === "goal")),
    onBack: () => {
      if (stepIndex === 0) router.replace("/account" as Href);
      else setStepIndex((current) => Math.max(0, current - 1));
    },
    onChange: (field, value) => setValues((current) => ({ ...current, [field]: value })),
    onChoosePlan: () => router.replace("/account" as Href),
    onLogin: () => setStepIndex(1),
    onNext: () => setStepIndex((current) => Math.min(onboardingJourneySteps.length - 1, current + 1)),
    values,
  }), [router, stepIndex, values]);

  if (status === "anonymous") return <Redirect href="/login" />;
  if (status !== "authenticated" || !session) return <LoadingState label="Preparando vista previa…" />;
  if (!session.is_staff) return <Redirect href="/account" />;

  return (
    <Screen contentStyle={{ paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 }} scroll={usesFixedDisclosuresFooter || usesFixedProfileChrome ? false : stepIndex >= 6 ? "auto" : false}>
      <OnboardingJourneyView
        conciseSexEyebrow
        contentSizedDietaryChips
        controller={controller}
        disclosuresTitleSpacingReduction={18}
        fixedDisclosuresFooter={usesFixedDisclosuresFooter}
        fixedLoginActionBottomSpacing={134}
        fixedProfileChrome={usesFixedProfileChrome}
        fixedProfileFooterBottomSpacing={46}
        fullWidthExplanationTransition
        hideCalculationReviewDisclosure
        measurementReferenceNotice
        progressiveAllergyDetails
        profileEyebrowsMuted
        profileProgressBottomSpacing={24}
        profileProgressEyebrowBottomSpacing={18}
        profileQuestionSpacing={24}
        profileProgressWidthReduction={36}
        profileTitleBottomSpacingReduction={12}
        showGoalOptionsEyebrow
        showProfileControlBleed
        storyboardSummaryLayout
        step={step as OnboardingJourneyStep}
        topInsetReduction={storyboardTopInsetReduction}
      />
    </Screen>
  );
}
