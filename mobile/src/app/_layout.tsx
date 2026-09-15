import * as Sentry from "@sentry/react-native";
import * as Notifications from "expo-notifications";
import { type ErrorBoundaryProps, type Href, Stack, usePathname, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { AppState, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider, useSession } from "@/auth/session-context";
import { ComparatorSelectionProvider } from "@/components/comparisons/comparator-selection-context";
import { AppNavigationHeader, AppNavigationProvider } from "@/components/navigation/app-navigation";
import { tokens } from "@/design/tokens";
import { clearNativeReminders, refreshNativeReminders } from "@/notifications/native-reminders";
import { notificationRoute } from "@/notifications/notification-navigation";
import "@/observability/sentry";

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
  const router = useRouter();
  const { status, profile } = useSession();

  useEffect(() => {
    if (status !== "authenticated" || !profile) return;
    const returnTo = pathname.startsWith("/share/") || pathname.startsWith("/s/") ? pathname : undefined;
    if (profile.review_disclosure_required && pathname !== "/disclosures") {
      router.replace(returnTo ? { pathname: "/disclosures", params: { returnTo } } : "/disclosures" as Href);
      return;
    }
    if (!profile.review_disclosure_required && !profile.onboarding_completed && pathname !== "/onboarding") {
      router.replace(returnTo ? { pathname: "/onboarding", params: { returnTo } } : "/onboarding" as Href);
    }
  }, [pathname, profile, router, status]);

  return null;
}

function NativeReminderReconciler() {
  const { status, apiRequest } = useSession();

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
      if (nextState === "active") reconcile();
    });
    return () => subscription.remove();
  }, [apiRequest, status]);

  return null;
}

function RootLayout() {
  const router = useRouter();

  useEffect(() => {
    if (Platform.OS === "web") return;
    const openNotification = (notification: Notifications.Notification) => {
      router.push(notificationRoute(notification.request.content.data));
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
          <AppNavigationProvider>
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
          </AppNavigationProvider>
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
