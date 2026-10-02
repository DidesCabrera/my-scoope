import { StyleSheet, Text, useWindowDimensions, View } from "react-native";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import type { AssistantAvailability } from "@/api/types";
import { tokens } from "@/design/tokens";

export function AssistantCreditBalance({ availability }: { availability: AssistantAvailability }) {
  const { width } = useWindowDimensions();

  return (
    <View style={[styles.panel, { width: Math.max(0, width - (tokens.layout.reducedInset * 2)) }]}>
      <Svg aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
        <Defs>
          <LinearGradient id="assistant-credit-macros" x1="0" x2="1" y1="0" y2="1">
            <Stop offset="0" stopColor={tokens.color.protein} />
            <Stop offset="0.5" stopColor={tokens.color.carbs} />
            <Stop offset="1" stopColor={tokens.color.fat} />
          </LinearGradient>
        </Defs>
        <Rect fill="url(#assistant-credit-macros)" height="100%" width="100%" />
      </Svg>
      <View accessibilityLabel={`${availability.available_credits} créditos disponibles`} accessible style={styles.balance}>
        <Text style={styles.value}>{availability.available_credits}</Text>
        <Text style={styles.label}>créditos disponibles</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  balance: { alignItems: "center", flex: 1, flexDirection: "row", flexShrink: 1, gap: tokens.spacing.xs, minWidth: 0 },
  label: { color: tokens.color.surfaceApp, flexShrink: 1, fontSize: tokens.type.caption, fontWeight: tokens.weight.medium, lineHeight: 18 },
  panel: { alignItems: "center", alignSelf: "stretch", borderColor: tokens.color.surfaceApp, borderRadius: tokens.radius.panel, borderWidth: 1, flexDirection: "row", gap: tokens.spacing.sm, justifyContent: "space-between", marginBottom: tokens.spacing.sm, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, minHeight: 54, minWidth: 0, overflow: "hidden", paddingHorizontal: tokens.card.outerPadding, paddingVertical: tokens.spacing.sm },
  value: { color: tokens.color.surfaceApp, fontSize: 18, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 22 },
});
