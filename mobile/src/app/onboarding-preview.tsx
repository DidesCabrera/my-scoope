import { type Href, Redirect, Stack, useRouter } from "expo-router";
import { useMemo, useState } from "react";

import { useSession } from "@/auth/session-context";
import {
  OnboardingJourneyView,
  type OnboardingJourneyController,
  type OnboardingJourneyStep,
  type OnboardingJourneyValues,
  onboardingJourneyPreviewValues,
  onboardingJourneySteps,
  presentationPropsForOnboardingStep,
} from "@/components/onboarding";
import { LoadingState, Screen } from "@/components/ui";

export default function OnboardingPreviewScreen() {
  const router = useRouter();
  const { session, status } = useSession();
  const [stepIndex, setStepIndex] = useState(0);
  const [values, setValues] = useState<OnboardingJourneyValues>({ ...onboardingJourneyPreviewValues });

  const step = onboardingJourneySteps[stepIndex]?.key ?? "login";
  const usesFixedDisclosuresFooter = stepIndex === 7;
  const usesFixedProfileChrome = stepIndex >= 8 && stepIndex <= 13;
  const headerCompensationTop = stepIndex >= 7 ? 88 : 0;
  const presentationProps = presentationPropsForOnboardingStep(step as OnboardingJourneyStep);
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
    <>
      <Stack.Screen options={{ gestureEnabled: false, headerShown: false }} />
      <Screen contentStyle={{ paddingBottom: 0, paddingHorizontal: 0, paddingTop: headerCompensationTop }} scroll={usesFixedDisclosuresFooter || usesFixedProfileChrome ? false : stepIndex >= 7 ? "auto" : false}>
        <OnboardingJourneyView
        controller={controller}
        {...presentationProps}
        step={step as OnboardingJourneyStep}
        />
      </Screen>
    </>
  );
}
