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
  divider: { backgroundColor: tokens.color.borderDefault, height: 1, marginBottom: tokens.spacing.sm, marginTop: tokens.spacing.lg },
  soft: { backgroundColor: tokens.color.borderSoft },
  compact: { marginBottom: 0, marginTop: tokens.spacing.sm },
  wide: { marginBottom: tokens.spacing.lg, marginTop: tokens.spacing.xxl },
});
