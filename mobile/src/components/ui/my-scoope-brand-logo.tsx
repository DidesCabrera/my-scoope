import { Image, StyleSheet, View } from "react-native";

const brandLogoSource = require("../../../assets/images/launch-logo.png");
const commercialLogoSource = require("../../../assets/images/commercial-logo.png");

export function MyScoopeBrandLogo({ commercial = false, compact = false, scale = 1 }: { commercial?: boolean; compact?: boolean; scale?: number }) {
  if (commercial) {
    return (
      <View accessibilityLabel="My Scoope" accessible style={styles.commercialFrame}>
        <Image resizeMode="contain" source={commercialLogoSource} style={styles.commercialLogo} />
      </View>
    );
  }
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
  commercialFrame: { height: 15, width: 90 },
  commercialLogo: { height: 15, width: 90 },
});
