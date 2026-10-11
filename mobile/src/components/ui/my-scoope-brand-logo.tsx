import { Image, StyleSheet } from "react-native";

const brandLogoSource = require("../../../assets/images/launch-logo.png");

export function MyScoopeBrandLogo({ compact = false, scale = 1 }: { compact?: boolean; scale?: number }) {
  const baseSize = compact ? styles.compactLogo : styles.logo;
  return (
    <Image
      accessibilityLabel="My Scoope"
      resizeMode="contain"
      source={brandLogoSource}
      style={[baseSize, scale !== 1 && { height: baseSize.height * scale, width: baseSize.width * scale }]}
    />
  );
}

const styles = StyleSheet.create({
  logo: { height: 33.6, width: 120 },
  compactLogo: { height: 28, width: 100 },
});
