import type { PropsWithChildren } from "react";
import { StyleProp, StyleSheet, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

export { Chip as Pill } from "./chip";

export function Card({
  children,
  accent,
  muted = false,
  style,
}: PropsWithChildren<{ accent?: string; muted?: boolean; style?: StyleProp<ViewStyle> }>) {
  return (
    <View style={[styles.card, muted && styles.cardMuted, accent ? { borderTopColor: accent, borderTopWidth: 3 } : null, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: tokens.color.surfaceCard, borderColor: "transparent", borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: -tokens.spacing.screen, padding: tokens.card.outerPadding },
  cardMuted: { backgroundColor: tokens.color.surfaceMuted },
});
