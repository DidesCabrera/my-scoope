import { Image, StyleSheet } from "react-native";

const brandLogoSource = require("../../../assets/images/launch-logo.png");

export function MyScoopeBrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <Image
      accessibilityLabel="My Scoope"
      resizeMode="contain"
      source={brandLogoSource}
      style={[styles.logo, compact && styles.compactLogo]}
    />
  );
}

const styles = StyleSheet.create({
  logo: { height: 33.6, width: 120 },
  compactLogo: { height: 28, width: 100 },
});
