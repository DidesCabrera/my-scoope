import * as Sentry from "@sentry/react-native";
import * as Notifications from "expo-notifications";
import { Stack, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider } from "@/auth/session-context";
import { tokens } from "@/design/tokens";
import "@/observability/sentry";

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
        <Stack
          screenOptions={{
            animation: "slide_from_right",
            contentStyle: { backgroundColor: tokens.color.surfaceApp },
            headerShown: false,
          }}
        />
        <StatusBar style="light" />
      </SessionProvider>
    </SafeAreaProvider>
  );
}

export default Sentry.wrap(RootLayout);
