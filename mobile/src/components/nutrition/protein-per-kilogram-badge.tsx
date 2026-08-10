import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

function formattedValue(value: number): string {
  const normalized = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(normalized);
}

export function ProteinPerKilogramBadge({
  value,
  density = "regular",
}: {
  value: number;
  density?: "compact" | "regular";
}) {
  const compact = density === "compact";
  return (
    <View
      accessibilityLabel={`Proteína por kilogramo: ${formattedValue(value)} gramos por kilogramo`}
      accessible
      style={[styles.badge, compact && styles.badgeCompact]}>
      <Text
        adjustsFontSizeToFit
        minimumFontScale={0.85}
        numberOfLines={1}
        style={[styles.text, compact && styles.textCompact]}>
        {formattedValue(value)} g/kg
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { alignItems: "center", backgroundColor: tokens.color.ppk, borderRadius: 5, justifyContent: "center", minHeight: 22, paddingHorizontal: 3 },
  badgeCompact: { minHeight: 18, paddingHorizontal: 3 },
  text: { color: "#111111", fontSize: 11, fontWeight: "800", fontVariant: ["tabular-nums"] },
  textCompact: { fontSize: 10 },
});
