import { type Href, Redirect, useLocalSearchParams } from "expo-router";

import { useSession } from "@/auth/session-context";
import { OnboardingJourneyView, onboardingJourneyPreviewValues } from "@/components/onboarding";
import { Screen } from "@/components/ui";
import { internalHref } from "@/navigation/internal-href";

export default function LoginScreen() {
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();
  const returnHref = internalHref(returnTo);
  const { status, profile, authBusy, authError, authReady, startSignIn } = useSession();

  if (status === "authenticated") {
    if (!profile?.onboarding_completed) return <Redirect href={{ pathname: "/onboarding", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    if (profile?.review_disclosure_required) return <Redirect href={{ pathname: "/disclosures", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    return <Redirect href={returnHref ?? ("/today" as Href)} />;
  }

  return (
    <Screen contentStyle={{ paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 }}>
      <OnboardingJourneyView
        controller={{
          busy: authBusy,
          error: authError,
          loginDisabled: !authReady,
          onLogin: () => void startSignIn(returnHref),
          values: onboardingJourneyPreviewValues,
        }}
        step="login"
      />
    </Screen>
  );
}
