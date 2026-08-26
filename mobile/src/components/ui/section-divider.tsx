import { type StyleProp, StyleSheet, View, type ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

type SectionDividerProps = {
  spacing?: "compact" | "regular" | "wide";
  tone?: "default" | "soft";
  style?: StyleProp<ViewStyle>;
};

export function SectionDivider({ spacing = "regular", tone = "default", style }: SectionDividerProps) {
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[
        styles.divider,
        tone === "soft" && styles.soft,
        spacing === "compact" && styles.compact,
        spacing === "wide" && styles.wide,
        style,
      ]}
    />
  );
}

const styles = StyleSheet.create({
  divider: { backgroundColor: tokens.color.borderDefault, height: 1, marginVertical: tokens.spacing.md },
  soft: { backgroundColor: tokens.color.borderSoft },
  compact: { marginVertical: tokens.spacing.xs },
  wide: { marginVertical: tokens.spacing.xl },
});
