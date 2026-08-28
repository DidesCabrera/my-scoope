import * as Sentry from "@sentry/react-native";
import * as Notifications from "expo-notifications";
import { type Href, Stack, usePathname, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider, useSession } from "@/auth/session-context";
import { ComparatorSelectionProvider } from "@/components/comparisons/comparator-selection-context";
import { AppNavigationHeader, AppNavigationProvider } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";
import "@/observability/sentry";

function AuthenticatedRouteGate() {
  const pathname = usePathname();
  const router = useRouter();
  const { status, profile } = useSession();

  useEffect(() => {
    if (status !== "authenticated" || !profile) return;
    if (profile.review_disclosure_required && pathname !== "/disclosures") {
      router.replace("/disclosures" as Href);
      return;
    }
    if (!profile.review_disclosure_required && !profile.onboarding_completed && pathname !== "/onboarding") {
      router.replace("/onboarding" as Href);
    }
  }, [pathname, profile, router, status]);

  return null;
}

function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    const subscription = Notifications.addNotificationResponseReceivedListener(() => {
      router.push("/today");
    });
    return () => subscription.remove();
  }, [router]);

  return (
    <SafeAreaProvider>
      <SessionProvider>
        <AppNavigationProvider>
          <ComparatorSelectionProvider>
            <AuthenticatedRouteGate />
            <Stack
              screenOptions={{
                animation: "slide_from_right",
                contentStyle: { backgroundColor: tokens.color.surfaceApp },
                header: () => <AppNavigationHeader />,
                headerShown: true,
              }}
            />
          </ComparatorSelectionProvider>
        </AppNavigationProvider>
        <StatusBar style="light" />
      </SessionProvider>
    </SafeAreaProvider>
  );
}

export default Sentry.wrap(RootLayout);
