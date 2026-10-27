import * as Sentry from "@sentry/react-native";
import * as Notifications from "expo-notifications";
import * as SplashScreen from "expo-splash-screen";
import { type ErrorBoundaryProps, type Href, Stack, useGlobalSearchParams, useNavigationContainerRef, usePathname, useRouter, useSegments } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useRef } from "react";
import { AppState, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider, useSession } from "@/auth/session-context";
import { StoreBillingProvider } from "@/billing/store-billing-context";
import { ComparatorSelectionProvider } from "@/components/comparisons/comparator-selection-context";
import { AppNavigationHeader, AppNavigationProvider } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";
import { clearNativeReminders, refreshNativeReminders } from "@/notifications/native-reminders";
import { notificationRoute } from "@/notifications/notification-navigation";
import { recordNavigationRedirect, recordNavigationTransition } from "@/observability/navigation";
import { routeTemplateFromSegments } from "@/observability/sanitize";
import { sentryNavigationIntegration } from "@/observability/sentry";

if (Platform.OS !== "web") void SplashScreen.preventAutoHideAsync();

function ScreenErrorBoundary({ error, retry }: ErrorBoundaryProps) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <View style={styles.errorScreen}>
      <Text style={styles.errorTitle}>No pudimos mostrar esta vista</Text>
      <Text style={styles.errorMessage}>Tus datos siguen guardados. Puedes volver a intentarlo sin cerrar la aplicación.</Text>
      <Pressable
        accessibilityLabel="Reintentar abrir esta vista"
        accessibilityRole="button"
        onPress={() => void retry()}
        style={({ pressed }) => [styles.retryButton, pressed && styles.retryButtonPressed]}>
        <Text style={styles.retryLabel}>Reintentar</Text>
      </Pressable>
    </View>
  );
}

function AuthenticatedRouteGate() {
  const pathname = usePathname();
  const segments = useSegments();
  const routeTemplate = routeTemplateFromSegments(segments);
  const { dailyPlanId, origin } = useGlobalSearchParams<{ dailyPlanId?: string; origin?: string }>();
  const router = useRouter();
  const { status, profile } = useSession();

  useEffect(() => {
    if (status !== "authenticated" || !profile) return;
    const returnTo = pathname.startsWith("/share/") || pathname.startsWith("/s/") ? pathname : undefined;
    if (profile.review_disclosure_required && pathname !== "/disclosures" && pathname !== "/onboarding") {
      recordNavigationRedirect(routeTemplate, "/disclosures", "disclosure_required");
      router.replace(returnTo ? { pathname: "/disclosures", params: { returnTo } } : "/disclosures" as Href);
      return;
    }
    const isOnboardingSubscription = pathname === "/subscription" && origin === "onboarding";
    // The profile snapshot can still have the previous stage when accept-plan navigates here.
    const isOnboardingCalendar = pathname === "/calendar/select-plans" && origin === "onboarding"
      && Number.isSafeInteger(Number(dailyPlanId)) && Number(dailyPlanId) > 0;
    const isOnboardingMealDetail = /^\/onboarding\/minutas\/\d+\/meals\/\d+$/.test(pathname)
      && (profile.onboarding_stage === "plan" || profile.onboarding_stage === "plans");
    if (!profile.review_disclosure_required && !profile.onboarding_completed && pathname !== "/onboarding" && !isOnboardingSubscription && !isOnboardingCalendar && !isOnboardingMealDetail) {
      recordNavigationRedirect(routeTemplate, "/onboarding", "onboarding_required");
      router.replace(returnTo ? { pathname: "/onboarding", params: { returnTo } } : "/onboarding" as Href);
    }
  }, [dailyPlanId, origin, pathname, profile, routeTemplate, router, status]);

  return null;
}

function SplashCoordinator() {
  const { status } = useSession();

  useEffect(() => {
    if (status === "booting" || Platform.OS === "web") return undefined;
    const frame = requestAnimationFrame(() => { void SplashScreen.hideAsync(); });
    return () => cancelAnimationFrame(frame);
  }, [status]);

  return null;
}

function NativeReminderReconciler() {
  const { status, apiRequest } = useSession();
  const inactiveSince = useRef<number | null>(null);

  useEffect(() => {
    const reconcile = () => {
      if (status === "authenticated") {
        void refreshNativeReminders(apiRequest).catch(() => undefined);
      } else if (status === "anonymous") {
        void clearNativeReminders().catch(() => undefined);
      }
    };

    reconcile();
    const subscription = AppState.addEventListener("change", (nextState) => {
      if (nextState !== "active") {
        inactiveSince.current ??= Date.now();
        return;
      }
      const inactiveDuration = inactiveSince.current == null ? null : Date.now() - inactiveSince.current;
      inactiveSince.current = null;
      if (inactiveDuration != null && inactiveDuration >= 10_000) reconcile();
    });
    return () => subscription.remove();
  }, [apiRequest, status]);

  return null;
}

function RootLayout() {
  const router = useRouter();
  const navigationRef = useNavigationContainerRef();
  const segments = useSegments();
  const routeTemplate = routeTemplateFromSegments(segments);
  const previousRoute = useRef<string | null>(null);
  const currentRoute = useRef(routeTemplate);

  useEffect(() => {
    sentryNavigationIntegration.registerNavigationContainer(navigationRef);
  }, [navigationRef]);

  useEffect(() => {
    if (previousRoute.current === routeTemplate) return;
    recordNavigationTransition(previousRoute.current, routeTemplate);
    previousRoute.current = routeTemplate;
    currentRoute.current = routeTemplate;
  }, [routeTemplate]);

  useEffect(() => {
    if (Platform.OS === "web") return;
    const openNotification = (notification: Notifications.Notification) => {
      const target = notificationRoute(notification.request.content.data);
      recordNavigationRedirect(currentRoute.current, String(target), "notification_open");
      router.push(target);
    };
    const lastResponse = Notifications.getLastNotificationResponse();
    if (lastResponse?.notification) {
      openNotification(lastResponse.notification);
      Notifications.clearLastNotificationResponse();
    }
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      openNotification(response.notification);
      Notifications.clearLastNotificationResponse();
    });
    return () => subscription.remove();
  }, [router]);

  return (
    <GestureHandlerRootView style={styles.gestureRoot}>
      <SafeAreaProvider>
        <SessionProvider>
          <SplashCoordinator />
          <StoreBillingProvider><AppNavigationProvider>
            <ComparatorSelectionProvider>
              <AuthenticatedRouteGate />
              <NativeReminderReconciler />
              <Stack
                unstable_screenErrorBoundary={ScreenErrorBoundary}
                screenOptions={{
                  animation: "slide_from_right",
                  contentStyle: { backgroundColor: tokens.color.surfaceApp },
                  header: () => <AppNavigationHeader />,
                  headerShown: true,
                }}
              />
            </ComparatorSelectionProvider>
          </AppNavigationProvider></StoreBillingProvider>
          <StatusBar style="light" />
        </SessionProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  errorMessage: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 21, textAlign: "center" },
  errorScreen: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flex: 1, gap: tokens.spacing.md, justifyContent: "center", padding: tokens.spacing.screen },
  errorTitle: { color: tokens.color.textMain, fontSize: tokens.type.title, fontWeight: tokens.weight.bold, textAlign: "center" },
  gestureRoot: { flex: 1 },
  retryButton: { alignItems: "center", backgroundColor: tokens.color.interactivePrimary, borderRadius: tokens.radius.md, minHeight: 48, justifyContent: "center", paddingHorizontal: tokens.spacing.lg },
  retryButtonPressed: { opacity: 0.72 },
  retryLabel: { color: tokens.color.entityIconForeground, fontSize: tokens.type.caption, fontWeight: tokens.weight.bold },
});

export default Sentry.wrap(RootLayout);
