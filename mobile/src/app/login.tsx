import { type Href, Redirect, Stack, useLocalSearchParams } from "expo-router";

import { useSession } from "@/auth/session-context";
import { OnboardingJourneyView, onboardingJourneyPreviewValues } from "@/components/onboarding";
import { LoadingState, Screen } from "@/components/ui";
import { internalHref } from "@/navigation/internal-href";

export default function LoginScreen() {
  const { returnTo, emailConfirmed } = useLocalSearchParams<{ returnTo?: string; emailConfirmed?: string }>();
  const returnHref = internalHref(returnTo);
  const { status, profile, authBusy, authError, authReady, authRestorePending, retrySessionRestore, startSignIn } = useSession();
  if (status === "booting") return <LoadingState label="Reconectando tu cuenta…" />;

  if (status === "authenticated") {
    if (!profile?.onboarding_completed) return <Redirect href={{ pathname: "/onboarding", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    if (profile?.review_disclosure_required) return <Redirect href={{ pathname: "/disclosures", params: returnHref ? { returnTo: String(returnHref) } : {} }} />;
    return <Redirect href={returnHref ?? ("/today" as Href)} />;
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <Screen contentStyle={{ paddingBottom: 0, paddingHorizontal: 0, paddingTop: 0 }}>
        <OnboardingJourneyView
          controller={{
            busy: authBusy,
            error: authError,
            notice: emailConfirmed === "1" ? "Correo confirmado. Inicia sesión para continuar en My Scoope." : null,
            loginDisabled: !authReady && !authRestorePending,
            loginLabel: authRestorePending ? "Reintentar conexión" : undefined,
            onLogin: () => authRestorePending ? retrySessionRestore() : void startSignIn(returnHref),
            values: onboardingJourneyPreviewValues,
          }}
          step="login"
        />
      </Screen>
    </>
  );
}
