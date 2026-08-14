import type { PropsWithChildren } from "react";
import { StyleProp, StyleSheet, Text, View, ViewStyle } from "react-native";

import { tokens } from "@/design/tokens";

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

export function Pill({ label, color = tokens.color.interactivePrimary }: { label: string; color?: string }) {
  return (
    <View style={[styles.pill, { borderColor: color }]}>
      <Text style={[styles.pillText, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: tokens.color.surfaceCard, borderColor: tokens.color.borderSoft, borderRadius: tokens.radius.card, borderWidth: 1, gap: tokens.card.gap, marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding, padding: tokens.card.outerPadding },
  cardMuted: { backgroundColor: tokens.color.surfaceMuted },
  pill: { alignSelf: "flex-start", borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 5 },
  pillText: { fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 0.4 },
});
