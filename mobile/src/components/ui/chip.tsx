import { StyleSheet, Text, View } from "react-native";

import { tokens } from "@/design/tokens";

export type ChipProps = {
  backgroundColor?: string;
  borderColor?: string;
  color?: string;
  label: string;
  textColor?: string;
};

export function Chip({
  backgroundColor,
  borderColor,
  color,
  label,
  textColor,
}: ChipProps) {
  const resolvedBorderColor = borderColor ?? color ?? tokens.color.interactivePrimary;
  return (
    <View style={[styles.chip, { backgroundColor, borderColor: resolvedBorderColor }]}>
      <Text style={[styles.label, { color: textColor ?? resolvedBorderColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { alignSelf: "flex-start", borderRadius: tokens.radius.pill, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 5 },
  label: { fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 0.4 },
});
