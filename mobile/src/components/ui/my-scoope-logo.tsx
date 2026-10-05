import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export function MyScoopeLogo() {
  return (
    <View accessibilityLabel="My Scoope" accessible style={styles.logo}>
      <Text style={styles.logoText}>MyScoope</Text>
      <View aria-hidden style={styles.logoBars}>
        <View style={[styles.logoBar, styles.logoBarProtein]} />
        <View style={[styles.logoBar, styles.logoBarCarbs]} />
        <View style={[styles.logoBar, styles.logoBarFat]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  logo: { alignItems: "center", flexDirection: "row", gap: 5 },
  logoText: { color: tokens.color.textMain, fontSize: 18, fontWeight: "900", letterSpacing: -0.7 },
  logoBars: { gap: 2 },
  logoBar: { borderRadius: 2, height: 3, width: 13 },
  logoBarProtein: { backgroundColor: tokens.color.protein },
  logoBarCarbs: { backgroundColor: tokens.color.carbs },
  logoBarFat: { backgroundColor: tokens.color.fat },
});
