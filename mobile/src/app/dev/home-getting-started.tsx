import { Redirect, Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { Camera, Scale, Weight } from "lucide-react-native";
import { useEffect } from "react";
import { StyleSheet, Text, View } from "react-native";

import { CurrentWeekSection } from "@/components/calendarization/current-week-section";
import { HomeGettingStarted } from "@/components/home/home-getting-started";
import { HomeLibraryGrid } from "@/components/home/home-library-grid";
import { Button, GuideMetric, Screen } from "@/components/ui";
import { tokens } from "@/design/tokens";

export default function HomeGettingStartedPreview() {
  useEffect(() => {
    if (__DEV__) void SplashScreen.hideAsync();
  }, []);
  if (!__DEV__) return <Redirect href="/" />;
  return (
    <>
      <Stack.Screen options={{ animation: "none", headerShown: true }} />
      <Screen headerMode="preserve">
        <View style={styles.weekRow}><CurrentWeekSection localDate="2026-10-23" /></View>
        <View style={styles.greeting}>
          <View style={styles.greetingHeading}>
            <Text style={styles.greetingTitle}>💪🏻Vamos Felipe!</Text>
            <GuideMetric onPress={() => undefined} tone="ppk" value="88,2 kg" />
          </View>
          <Text style={styles.greetingSubtitle}>Fallar en planificar, es planificar fallar</Text>
        </View>
        <HomeGettingStarted />
        <HomeLibraryGrid counts={{ dailyPlan: 3, food: 16, meal: 24, program: 1 }} />
        <View style={styles.quickActions}>
          <Text accessibilityRole="header" style={styles.sectionTitle}>Accesos rápidos</Text>
          <View style={styles.quickActionButtons}>
            <Button icon={<Camera color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Digitalizar etiqueta" onPress={() => undefined} variant="secondary" />
            <Button icon={<Weight color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Registrar peso corporal" onPress={() => undefined} variant="secondary" />
            <Button icon={<Scale color={tokens.color.textMain} size={20} strokeWidth={2} />} label="Comparar" onPress={() => undefined} variant="secondary" />
          </View>
        </View>
      </Screen>
    </>
  );
}

const styles = StyleSheet.create({
  greeting: { gap: tokens.spacing.xs },
  greetingHeading: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between" },
  greetingSubtitle: { color: tokens.color.textMuted, fontSize: tokens.type.caption, lineHeight: 20 },
  greetingTitle: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.title, fontWeight: tokens.weight.extraBold, letterSpacing: -0.5 },
  quickActionButtons: { gap: tokens.spacing.sm, marginTop: tokens.spacing.sm },
  quickActions: { marginTop: tokens.spacing.xl },
  sectionTitle: { color: tokens.color.textMain, fontSize: 18, fontWeight: tokens.weight.semibold },
  weekRow: { marginBottom: tokens.spacing.sm },
});
