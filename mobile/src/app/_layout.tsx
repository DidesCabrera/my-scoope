import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider } from "@/auth/session-context";
import { tokens } from "@/design/tokens";

export default function RootLayout() {
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
